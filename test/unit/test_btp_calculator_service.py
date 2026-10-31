# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for BondCalculatorService on fixed-rate BTPs.

The parametrised test runs every "btp_calculator_case_*.json" fixture. Expected
values come from the `Bond` sheet of the reference spreadsheet
(docs/ObbligazioniTF v5.0.ods, F6 = 2): each key ends with the cell it was taken
from (e.g. "load_price_K26"). The cases cover:
  - the issue discount (scarto di emissione, Fase 8): bonds issued below par bought
    above and below the theoretical price, an early sale, a bond issued above par
    and one issued before 1997;
  - the accrued interest (rateo) and its taxes for purchases and sales in the
    middle of a coupon period, the zainetto offsetting a capital gain and sale
    commissions ignored at maturity (Fase 9).
"""
import json
from datetime import date
from pathlib import Path

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services.bond_calculator_service import BondCalculatorService
from intelligent_investor.utils.coupon_schedule import CouponSchedule
from intelligent_investor.utils.duration import modified_duration
from intelligent_investor.utils.yield_calculator import xirr

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

_ABS_EURO = 1e-2  # ± 0.01 €
_ABS_PRICE = 1e-4  # ± 0.0001 per 100 of nominal
_ABS_YIELD = 1e-3  # ± 0.001 percentage points


def _load_cases() -> list[tuple[str, dict]]:
    """Return [(test_id, case_dict), ...] for every BTP fixture file."""
    return [
        (path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(_FIXTURES_DIR.glob("btp_calculator_case_*.json"))
    ]


_CASES = _load_cases()


def _make_bond(raw: dict) -> BondDTO:
    dates = {key: date.fromisoformat(raw[key]) for key in ("issue_date", "maturity_date")}
    return BondDTO(**{**raw, **dates})


def _make_transaction(raw: dict) -> BondTransactionDTO:
    return BondTransactionDTO.from_flat(
        bond_id=0, **{key: date.fromisoformat(value) if key.endswith("_date") else value for key, value in raw.items()}
    )


# ---------------------------------------------------------------------------
# Cases cross-checked against the reference spreadsheet
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("test_id,case", _CASES, ids=[c[0] for c in _CASES])
def test_btp_matches_reference_spreadsheet(test_id: str, case: dict) -> None:
    result = BondCalculatorService().calculate(_make_transaction(case["transaction"]), _make_bond(case["bond"]))
    expected = case["expected"]

    exp_p = expected["purchase"]
    assert result.purchase.accrued_interest == pytest.approx(exp_p["accrued_interest_F36"], abs=_ABS_PRICE)
    assert result.purchase.accrued_interest_tax == pytest.approx(exp_p["accrued_interest_tax_K28"], abs=_ABS_EURO)
    assert result.purchase.unit_discount == pytest.approx(exp_p["unit_discount_F30"], abs=_ABS_PRICE)
    assert result.purchase.discount_tax == pytest.approx(exp_p["discount_tax_K27"], abs=_ABS_EURO)
    assert result.purchase.commission == pytest.approx(exp_p["commission_K24"], abs=_ABS_EURO)
    assert result.purchase.total_paid == pytest.approx(exp_p["total_paid_K29"], abs=_ABS_EURO)

    exp_s = expected["sale"]
    assert result.sale.accrued_interest == pytest.approx(exp_s["accrued_interest_F52"], abs=_ABS_PRICE)
    assert result.sale.accrued_interest_tax == pytest.approx(exp_s["accrued_interest_tax_K40"], abs=_ABS_EURO)
    assert result.sale.unit_discount == pytest.approx(exp_s["unit_discount_F46"], abs=_ABS_PRICE)
    assert result.sale.discount_tax == pytest.approx(exp_s["discount_tax_K39_F16"], abs=_ABS_EURO)
    assert result.sale.commission == pytest.approx(exp_s["commission_K36"], abs=_ABS_EURO)

    exp_cg = expected["capital_gain"]
    cg = result.capital_gain
    assert cg is not None
    assert cg.theoretical_purchase_price == pytest.approx(exp_cg["theoretical_purchase_price_F29"], abs=_ABS_PRICE)
    assert cg.theoretical_sale_price == pytest.approx(exp_cg["theoretical_sale_price_F45"], abs=_ABS_PRICE)
    assert cg.load_price == pytest.approx(exp_cg["load_price_K26"], abs=_ABS_PRICE)
    assert cg.unload_price == pytest.approx(exp_cg["unload_price_K38"], abs=_ABS_PRICE)
    assert cg.unit_gain_loss == pytest.approx(exp_cg["unit_gain_loss_K46"], abs=_ABS_PRICE)
    assert cg.total_gain_loss == pytest.approx(exp_cg["total_gain_loss_K48"], abs=_ABS_EURO)
    assert cg.capital_gain_tax == pytest.approx(exp_cg["capital_gain_tax_K52"], abs=_ABS_EURO)
    assert cg.remaining_loss == pytest.approx(exp_cg["remaining_loss_K53"], abs=_ABS_EURO)

    assert len(result.coupon_plan) == expected["coupons_in_holding"]

    exp_su = expected["summary"]
    assert result.summary.gross_gain == pytest.approx(exp_su["gross_gain_K10"], abs=_ABS_EURO)
    assert result.summary.compound_gross_yield == pytest.approx(exp_su["compound_gross_yield_K9"], abs=_ABS_YIELD)
    assert result.summary.net_gain_before_duty == pytest.approx(exp_su["net_gain_before_duty_K7"], abs=_ABS_EURO)
    assert result.summary.compound_net_yield_before_duty == pytest.approx(
        exp_su["compound_net_yield_before_duty_K6"], abs=_ABS_YIELD
    )


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


def test_asta_commission_based_on_face_value() -> None:
    bond = BondDTO(
        name="BTP TF test asta",
        isin="IT0000000002",
        bond_type="BTP",
        issue_date=date(2023, 2, 14),
        maturity_date=date(2025, 2, 14),
        issue_price=95.0,
        nominal_rate=3.0,
        coupon_frequency=2,
    )
    tx = BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="asta",
        purchase_date=date(2023, 2, 14),
        purchase_price=95.0,
        face_value=10000.0,
        buy_commission_pct=0.10,
    )

    result = BondCalculatorService().calculate(tx, bond)

    # At auction the commission is on face_value (10000), not on the clean amount (9500)
    assert result.purchase.commission == pytest.approx(10.0, abs=_ABS_EURO)
    # Unlike a BOT, a BTP bought at auction still gets a capital gain section
    assert result.capital_gain is not None


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
    tx = BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2024, 1, 15),  # exact stacco date
        purchase_price=100.0,
        face_value=10000.0,
        sale_date=date(2024, 10, 1),  # between the 2024-07-15 and 2025-01-15 stacchi
        sale_price=101.0,
    )

    result = BondCalculatorService().calculate(tx, bond)

    # Buying exactly on a stacco date: no accrued interest owed to the seller,
    # and that same-day coupon belongs to the seller, not this holder.
    assert result.purchase.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    assert [cp.payment_date for cp in result.coupon_plan] == [date(2024, 7, 15)]

    # Selling mid-period: buyer owes the running rateo to this seller.
    cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency, bond.nominal_rate, bond.tax_rate)
    assert tx.sell is not None
    expected_sale_accrued = cs.accrued_interest(tx.sell.date)
    assert expected_sale_accrued > 0
    assert result.sale.accrued_interest == pytest.approx(expected_sale_accrued, abs=_ABS_PRICE)
    assert result.sale.dirty_price == pytest.approx(101.0 + expected_sale_accrued, abs=_ABS_PRICE)

    # Issued at par: no issue discount on either leg
    assert result.purchase.discount_tax == 0.0
    assert result.sale.discount_tax == 0.0


def test_auction_purchase_cashes_prorated_first_coupon() -> None:
    # Issued 01/03/2028 inside the regular period 15/01 → 15/07: the first coupon
    # pays only the 136 of the 182 days accrued since issue (cell W4)
    bond = BondDTO(
        name="BTP TF prima cedola corta",
        isin="IT0000000005",
        bond_type="BTP",
        issue_date=date(2028, 3, 1),
        maturity_date=date(2030, 7, 15),
        issue_price=100.0,
        nominal_rate=3.6,
        coupon_frequency=2,
        tax_rate=12.5,
    )
    tx = BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="asta",
        purchase_date=date(2028, 3, 1),
        purchase_price=100.0,
        face_value=10000.0,
    )

    result = BondCalculatorService().calculate(tx, bond)

    assert result.purchase.accrued_interest == pytest.approx(0.0, abs=_ABS_PRICE)
    first, *others = result.coupon_plan
    assert first.payment_date == date(2028, 7, 15)
    assert first.gross_amount == pytest.approx(1.8 * 136 / 182, abs=_ABS_PRICE)
    assert [cp.gross_amount for cp in others] == pytest.approx([1.8] * 4)
    # Held to maturity at par: the gross gain is just the coupons cashed
    assert result.summary.gross_gain == pytest.approx((1.8 * 136 / 182 + 1.8 * 4) * 100, abs=_ABS_EURO)


def test_long_first_coupon_from_bond_first_coupon_date() -> None:
    bond = BondDTO(
        name="BTP TF prima cedola lunga",
        isin="IT0000000006",
        bond_type="BTP",
        issue_date=date(2028, 6, 1),
        maturity_date=date(2030, 7, 15),
        first_coupon_date=date(2029, 1, 15),
        issue_price=100.0,
        nominal_rate=3.6,
        coupon_frequency=2,
        tax_rate=12.5,
    )
    tx = BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2028, 10, 1),
        purchase_price=100.0,
        face_value=10000.0,
    )

    result = BondCalculatorService().calculate(tx, bond)

    # Rateo on the long period 15/01/2028 → 15/01/2029, accrued from issue (cell F36)
    assert result.purchase.accrued_interest == pytest.approx(3.6 * 122 / 366, abs=_ABS_PRICE)
    assert [cp.payment_date for cp in result.coupon_plan][0] == date(2029, 1, 15)
    assert result.coupon_plan[0].gross_amount == pytest.approx(3.6 * 228 / 366, abs=_ABS_PRICE)


# ---------------------------------------------------------------------------
# Modified duration (cell K16)
# ---------------------------------------------------------------------------


def _btp_lug29() -> BondDTO:
    return BondDTO(
        name="Btp Fx 3.35% Jul29 Eur",
        isin="IT0005584849",
        bond_type="BTP",
        issue_date=date(2024, 3, 1),
        maturity_date=date(2029, 7, 1),
        issue_price=99.82,
        nominal_rate=3.35,
        coupon_frequency=2,
        tax_rate=12.5,
    )


def _mot_purchase(sale_date: date | None = None) -> BondTransactionDTO:
    return BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2026, 10, 29),
        purchase_price=99.18,
        face_value=10000.0,
        buy_commission_pct=0.10,
        buy_commission_min=5.0,
        sale_date=sale_date,
        sale_price=100.5 if sale_date else None,
    )


def test_modified_duration_on_net_yield_to_maturity() -> None:
    summary = BondCalculatorService().calculate(_mot_purchase(), _btp_lug29()).summary

    # MDURATION(purchase; maturity; rate; K4 = net yield; frequency), basis 0
    expected = modified_duration(date(2026, 10, 29), date(2029, 7, 1), 3.35, summary.compound_net_yield, 2)
    assert summary.modified_duration == pytest.approx(expected)
    assert summary.modified_duration == pytest.approx(2.51, abs=0.01)


def test_modified_duration_uses_maturity_even_with_an_early_sale() -> None:
    summary = BondCalculatorService().calculate(_mot_purchase(sale_date=date(2027, 12, 15)), _btp_lug29()).summary

    expected = modified_duration(date(2026, 10, 29), date(2029, 7, 1), 3.35, summary.compound_net_yield, 2)
    assert summary.modified_duration == pytest.approx(expected)


def test_modified_duration_blank_for_holding_under_365_days() -> None:
    # Sold after 364 days (cell M15 < 365): the sheet leaves K16 blank
    summary = BondCalculatorService().calculate(_mot_purchase(sale_date=date(2027, 10, 28)), _btp_lug29()).summary

    assert summary.modified_duration is None


# ---------------------------------------------------------------------------
# Fixed fee per coupon (cell K44) and stamp duty year by year (column R)
# ---------------------------------------------------------------------------


def _with_coupon_fee(tx: BondTransactionDTO, fee: float) -> BondTransactionDTO:
    """The same transaction held in an account charging *fee* € per coupon."""
    return tx.model_copy(update={"account": tx.account.model_copy(update={"coupon_fee": fee})})


def test_coupon_fee_reduces_every_net_coupon() -> None:
    no_fee = BondCalculatorService().calculate(_mot_purchase(), _btp_lug29())
    tx = _mot_purchase()
    fee = BondCalculatorService().calculate(_with_coupon_fee(tx, 2.0), _btp_lug29())

    coupons = len(fee.coupon_plan)
    assert coupons == 6
    assert fee.coupon_fee == 2.0
    assert fee.summary.net_gain == pytest.approx(no_fee.summary.net_gain - 2.0 * coupons)
    assert fee.summary.net_gain_before_duty == pytest.approx(no_fee.summary.net_gain_before_duty - 2.0 * coupons)
    # The gross figures leave bank costs out, as the sheet with "Lordo senza Commissioni"
    assert fee.summary.gross_gain == pytest.approx(no_fee.summary.gross_gain)
    assert fee.summary.compound_gross_yield == pytest.approx(no_fee.summary.compound_gross_yield)
    assert fee.summary.compound_net_yield_before_duty < no_fee.summary.compound_net_yield_before_duty


def test_coupon_fee_not_charged_on_a_sale_between_coupons() -> None:
    # Sold on 15/12/2027: two coupons cashed (01/01 and 01/07/2027), the running one is rateo
    tx = _mot_purchase(sale_date=date(2027, 12, 15))
    no_fee = BondCalculatorService().calculate(tx, _btp_lug29())
    fee = BondCalculatorService().calculate(_with_coupon_fee(tx, 3.0), _btp_lug29())

    assert fee.summary.net_gain == pytest.approx(no_fee.summary.net_gain - 3.0 * 2)


def test_net_yield_takes_stamp_duty_out_year_by_year() -> None:
    result = BondCalculatorService().calculate(_mot_purchase(), _btp_lug29())
    duty = result.stamp_duty.estimated_duty
    quantity = result.quantity

    # Column R by hand: purchase 29/10/2026, maturity 01/07/2029 -> 3 calendar years,
    # duty / 3 taken from the first flow of 2027, 2028 and 2029
    flows = [(date(2026, 10, 29), -result.purchase.total_paid)]
    flows += [(cp.payment_date, cp.net_amount * quantity) for cp in result.coupon_plan]
    flows += [(date(2029, 7, 1), result.sale.total_received)]
    per_year = duty / 3
    by_hand = [flows[0]] + [
        (d, amount - per_year if d.year != flows[i][0].year else amount) for i, (d, amount) in enumerate(flows[1:])
    ]

    assert result.summary.compound_net_yield == pytest.approx(xirr(by_hand), abs=1e-9)
    # Taking it all from the last flow, as before, gives a slightly higher yield
    all_at_end = flows[:-1] + [(flows[-1][0], flows[-1][1] - duty)]
    assert result.summary.compound_net_yield < xirr(all_at_end)
