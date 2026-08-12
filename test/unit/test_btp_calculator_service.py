# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for BtpCalculatorService.

Unlike test_bot_calculator_service.py (JSON fixtures cross-checked against a
reference spreadsheet), these tests build the expected values in Python from
the same already-tested building blocks the service itself composes
(CouponSchedule, xirr, YieldCalculator, bond_calculator_common) — there is no
BTP reference spreadsheet yet (see docs/roadmap-btp.md, Fase 9). This checks
that BtpCalculatorService wires those pieces together correctly (which base
each amount is computed on, in which order taxes/duty are deducted), not the
correctness of the primitives themselves.
"""
from datetime import date

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.btp_transaction import BtpTransactionDTO
from intelligent_investor.services.bond_calculator_common import calc_stamp_duty
from intelligent_investor.services.btp_calculator_service import BtpCalculatorService
from intelligent_investor.utils.coupon_schedule import CouponSchedule
from intelligent_investor.utils.yield_calculator import YieldCalculator, xirr

_ABS_EURO = 1e-2
_ABS_PRICE = 1e-4
_ABS_YIELD = 1e-2


# ---------------------------------------------------------------------------
# Zero-coupon BTP (coupon_frequency=0) — degenerates to a 2-flow, BOT-like case
# ---------------------------------------------------------------------------


def test_zero_coupon_held_to_maturity() -> None:
    bond = BondDTO(
        name="BTP TF test ZC",
        isin="IT0000000001",
        bond_type="BTP",
        issue_date=date(2023, 2, 14),
        maturity_date=date(2025, 2, 14),
        issue_price=95.0,
        redemption_price=100.0,
        nominal_rate=0.0,
        coupon_frequency=0,
        tax_rate=12.5,
    )
    tx = BtpTransactionDTO(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2023, 6, 1),
        purchase_price=95.0,
        face_value=10000.0,
        buy_commission_pct=0.24,
        buy_commission_min=3.0,
        buy_commission_fixed=3.5,
        sell_commission_pct=0.19,
        sell_commission_min=2.5,
        sell_commission_fixed=3.5,
        stamp_duty_period="quarterly",
    )

    result = BtpCalculatorService().calculate(tx, bond)

    assert result.quantity == pytest.approx(100.0)

    # -- purchase: coupon_frequency=0 -> no accrued interest, dirty == clean --
    assert result.purchase.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    assert result.purchase.dirty_amount == pytest.approx(9500.0, abs=_ABS_EURO)
    assert result.purchase.commission == pytest.approx(22.8, abs=_ABS_EURO)  # max(9500*0.24%, 3.0)
    assert result.purchase.total_paid == pytest.approx(9526.3, abs=_ABS_EURO)

    assert result.coupon_plan == []

    # -- sale (redemption at par) --
    assert result.sale.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    assert result.sale.dirty_amount == pytest.approx(10000.0, abs=_ABS_EURO)
    assert result.sale.commission == pytest.approx(19.0, abs=_ABS_EURO)  # max(10000*0.19%, 2.5)

    # -- capital gain: pure clean-price gap, commissions spread per unit --
    cg = result.capital_gain
    assert cg.load_price == pytest.approx(95.263, abs=_ABS_PRICE)
    assert cg.unload_price == pytest.approx(99.775, abs=_ABS_PRICE)
    assert cg.total_gain_loss == pytest.approx(451.2, abs=_ABS_EURO)
    assert cg.capital_gain_tax == pytest.approx(56.4, abs=_ABS_EURO)
    assert cg.remaining_loss == pytest.approx(0.0, abs=_ABS_EURO)

    # sale.total_received has the capital gain tax withheld
    assert result.sale.total_received == pytest.approx(9921.1, abs=_ABS_EURO)

    # -- stamp duty --
    assert result.stamp_duty.holding_periods == 7
    assert result.stamp_duty.estimated_duty == pytest.approx(34.125, abs=_ABS_EURO)

    # -- summary --
    su = result.summary
    assert su.gross_gain == pytest.approx(500.0, abs=_ABS_EURO)
    assert su.net_gain_before_duty == pytest.approx(394.8, abs=_ABS_EURO)
    assert su.net_gain == pytest.approx(360.675, abs=_ABS_EURO)

    yc = YieldCalculator(tx.purchase_date, bond.maturity_date)
    assert su.simple_gross_yield == pytest.approx(
        yc.simple(su.gross_gain, result.purchase.dirty_amount), abs=_ABS_YIELD
    )
    # 2-flow XIRR must match the closed-form compound() (no intermediate coupons)
    assert su.compound_gross_yield == pytest.approx(
        yc.compound(result.sale.dirty_amount, result.purchase.dirty_amount), abs=_ABS_YIELD
    )
    assert su.simple_net_yield_before_duty == pytest.approx(
        yc.simple(su.net_gain_before_duty, result.purchase.total_paid), abs=_ABS_YIELD
    )
    assert su.compound_net_yield_before_duty == pytest.approx(
        yc.compound(result.sale.total_received, result.purchase.total_paid), abs=_ABS_YIELD
    )
    assert su.simple_net_yield == pytest.approx(
        yc.simple(su.net_gain, result.purchase.total_paid), abs=_ABS_YIELD
    )
    assert su.compound_net_yield == pytest.approx(
        yc.compound(result.sale.total_received - result.stamp_duty.estimated_duty, result.purchase.total_paid),
        abs=_ABS_YIELD,
    )


def test_asta_commission_based_on_face_value() -> None:
    bond = BondDTO(
        name="BTP TF test asta",
        isin="IT0000000002",
        bond_type="BTP",
        issue_date=date(2023, 2, 14),
        maturity_date=date(2025, 2, 14),
        issue_price=95.0,
        coupon_frequency=0,
    )
    tx = BtpTransactionDTO(
        bond_id=0,
        purchase_venue="asta",
        purchase_date=date(2023, 2, 14),
        purchase_price=95.0,
        face_value=10000.0,
        buy_commission_pct=0.10,
    )

    result = BtpCalculatorService().calculate(tx, bond)

    # asta commission is on face_value (10000), not on dirty_amount (9500)
    assert result.purchase.commission == pytest.approx(10.0, abs=_ABS_EURO)


# ---------------------------------------------------------------------------
# Semi-annual coupon BTP, held to maturity
# ---------------------------------------------------------------------------


def test_semiannual_coupon_held_to_maturity() -> None:
    bond = BondDTO(
        name="BTP TF 2028",
        isin="IT0000000003",
        bond_type="BTP",
        issue_date=date(2023, 1, 15),
        maturity_date=date(2028, 1, 15),
        issue_price=100.0,
        redemption_price=100.0,
        nominal_rate=3.6,
        coupon_frequency=2,
        tax_rate=12.5,
    )
    tx = BtpTransactionDTO(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2024, 4, 15),
        purchase_price=99.0,
        face_value=10000.0,
        stamp_duty_period="quarterly",
    )

    result = BtpCalculatorService().calculate(tx, bond)
    quantity = 100.0

    cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency, bond.nominal_rate, bond.tax_rate)
    expected_coupons = [cp for cp in cs.schedule if tx.purchase_date < cp.payment_date <= bond.maturity_date]

    # -- coupon plan: only stacchi after purchase, up to and including maturity --
    assert [cp.payment_date for cp in result.coupon_plan] == [cp.payment_date for cp in expected_coupons]
    assert len(result.coupon_plan) == 8

    # -- purchase: accrued interest from the previous stacco --
    expected_purchase_accrued = cs.accrued_interest(tx.purchase_date)
    assert result.purchase.accrued_interest == pytest.approx(expected_purchase_accrued, abs=_ABS_PRICE)
    purchase_dirty_amount = (tx.purchase_price + expected_purchase_accrued) * quantity
    assert result.purchase.dirty_amount == pytest.approx(purchase_dirty_amount, abs=_ABS_EURO)
    assert result.purchase.total_paid == pytest.approx(purchase_dirty_amount, abs=_ABS_EURO)  # no commissions

    # -- sale: redemption exactly on the last stacco -> zero accrued --
    assert result.sale.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    sale_dirty_amount = 100.0 * quantity
    assert result.sale.dirty_amount == pytest.approx(sale_dirty_amount, abs=_ABS_EURO)

    # -- capital gain: pure clean-price gap (99 -> 100), no commissions --
    cg = result.capital_gain
    assert cg.load_price == pytest.approx(99.0, abs=_ABS_PRICE)
    assert cg.unload_price == pytest.approx(100.0, abs=_ABS_PRICE)
    assert cg.total_gain_loss == pytest.approx(100.0, abs=_ABS_EURO)
    assert cg.capital_gain_tax == pytest.approx(12.5, abs=_ABS_EURO)

    sale_total_received = sale_dirty_amount - cg.capital_gain_tax
    assert result.sale.total_received == pytest.approx(sale_total_received, abs=_ABS_EURO)

    # -- stamp duty: same shared helper the service calls --
    expected_stamp_duty = calc_stamp_duty(
        duty_base_amount=purchase_dirty_amount,
        face_value=tx.face_value,
        purchase_date=tx.purchase_date,
        sale_date=bond.maturity_date,
        stamp_duty_period=tx.stamp_duty_period,
    )
    assert result.stamp_duty.holding_periods == expected_stamp_duty.holding_periods
    assert result.stamp_duty.estimated_duty == pytest.approx(expected_stamp_duty.estimated_duty, abs=_ABS_EURO)

    # -- summary: gross/net gain composed from coupons + sale - purchase --
    gross_coupons = sum(cp.gross_amount for cp in expected_coupons) * quantity
    net_coupons = sum(cp.net_amount for cp in expected_coupons) * quantity

    gross_gain = gross_coupons + sale_dirty_amount - purchase_dirty_amount
    net_gain_before_duty = net_coupons + sale_total_received - purchase_dirty_amount
    net_gain = net_gain_before_duty - expected_stamp_duty.estimated_duty

    assert result.summary.gross_gain == pytest.approx(gross_gain, abs=_ABS_EURO)
    assert result.summary.net_gain_before_duty == pytest.approx(net_gain_before_duty, abs=_ABS_EURO)
    assert result.summary.net_gain == pytest.approx(net_gain, abs=_ABS_EURO)

    # -- compound yields: multi-flow XIRR built the same way the service does --
    gross_cashflows = (
        [(tx.purchase_date, -purchase_dirty_amount)]
        + [(cp.payment_date, cp.gross_amount * quantity) for cp in expected_coupons]
        + [(bond.maturity_date, sale_dirty_amount)]
    )
    assert result.summary.compound_gross_yield == pytest.approx(xirr(gross_cashflows), abs=_ABS_YIELD)

    net_cashflows_before_duty = (
        [(tx.purchase_date, -purchase_dirty_amount)]
        + [(cp.payment_date, cp.net_amount * quantity) for cp in expected_coupons]
        + [(bond.maturity_date, sale_total_received)]
    )
    assert result.summary.compound_net_yield_before_duty == pytest.approx(
        xirr(net_cashflows_before_duty), abs=_ABS_YIELD
    )

    net_cashflows = (
        [(tx.purchase_date, -purchase_dirty_amount)]
        + [(cp.payment_date, cp.net_amount * quantity) for cp in expected_coupons]
        + [(bond.maturity_date, sale_total_received - expected_stamp_duty.estimated_duty)]
    )
    assert result.summary.compound_net_yield == pytest.approx(xirr(net_cashflows), abs=_ABS_YIELD)


# ---------------------------------------------------------------------------
# Early sale before the next coupon date, and purchase exactly on a stacco
# ---------------------------------------------------------------------------


def test_purchase_on_stacco_and_early_sale_before_next_coupon() -> None:
    bond = BondDTO(
        name="BTP TF 2028",
        isin="IT0000000004",
        bond_type="BTP",
        issue_date=date(2023, 1, 15),
        maturity_date=date(2028, 1, 15),
        issue_price=100.0,
        nominal_rate=3.6,
        coupon_frequency=2,
        tax_rate=12.5,
    )
    tx = BtpTransactionDTO(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2024, 1, 15),  # exact stacco date
        purchase_price=100.0,
        face_value=10000.0,
        sale_date=date(2024, 10, 1),  # between the 2024-07-15 and 2025-01-15 stacchi
        sale_price=101.0,
    )

    result = BtpCalculatorService().calculate(tx, bond)

    # Buying exactly on a stacco date: no accrued interest owed to the seller,
    # and that same-day coupon belongs to the seller, not this holder.
    assert result.purchase.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    assert [cp.payment_date for cp in result.coupon_plan] == [date(2024, 7, 15)]

    # Selling mid-period: buyer owes the running rateo to this seller.
    cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency, bond.nominal_rate, bond.tax_rate)
    expected_sale_accrued = cs.accrued_interest(tx.sale_date)
    assert expected_sale_accrued > 0
    assert result.sale.accrued_interest == pytest.approx(expected_sale_accrued, abs=_ABS_PRICE)
    assert result.sale.dirty_price == pytest.approx(101.0 + expected_sale_accrued, abs=_ABS_PRICE)
