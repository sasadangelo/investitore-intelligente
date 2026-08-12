# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the bond catalogue yield helpers in bond_controller.py (Fase 5).

Pure functions — no DB, no Flask request context, no I/O.
Covers:
  - _calc_btp_yields: coupon-schedule + multi-flow XIRR yield-to-maturity estimate
  - _calc_bond_yields: dispatch to the BTP vs BOT formula by bond_type
"""
from datetime import date

import pytest

from intelligent_investor.controllers.bond_controller import _calc_bond_yields, _calc_btp_yields, _calc_yields
from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.utils.yield_calculator import YieldCalculator

TODAY = date(2026, 7, 1)


def _make_btp(
    issue_date: date = date(2020, 7, 1),
    maturity_date: date = date(2027, 7, 1),
    coupon_frequency: int = 1,
    nominal_rate: float = 4.0,
    redemption_price: float = 100.0,
    tax_rate: float = 12.5,
) -> BondDTO:
    return BondDTO(
        name="BTP Test",
        isin="IT0005000099",
        bond_type="BTP",
        issue_date=issue_date,
        maturity_date=maturity_date,
        issue_price=99.0,
        redemption_price=redemption_price,
        nominal_rate=nominal_rate,
        coupon_frequency=coupon_frequency,
        tax_rate=tax_rate,
    )


def _make_bot(
    issue_date: date = date(2026, 1, 1),
    maturity_date: date = date(2027, 1, 1),
) -> BondDTO:
    return BondDTO(
        name="BOT Test",
        isin="IT0005000001",
        bond_type="BOT",
        issue_date=issue_date,
        maturity_date=maturity_date,
        issue_price=97.0,
    )


# ------------------------------------------------------------------
# _calc_btp_yields — edge cases
# ------------------------------------------------------------------


def test_btp_yields_none_when_already_matured() -> None:
    bond = _make_btp(maturity_date=TODAY)
    assert _calc_btp_yields(bond, last_price=99.0, today=TODAY) == (None, None)


def test_btp_yields_none_when_price_not_positive() -> None:
    bond = _make_btp()
    assert _calc_btp_yields(bond, last_price=0.0, today=TODAY) == (None, None)
    assert _calc_btp_yields(bond, last_price=-1.0, today=TODAY) == (None, None)


def test_btp_yields_zero_coupon_matches_compound_formula() -> None:
    """coupon_frequency=0 degenerates to a two-flow XIRR, which must equal
    YieldCalculator.compound() — same reduction documented for xirr()."""
    bond = _make_btp(coupon_frequency=0, nominal_rate=0.0, redemption_price=100.0)
    last_price = 95.0

    gross, net = _calc_btp_yields(bond, last_price=last_price, today=TODAY)

    yc = YieldCalculator(TODAY, bond.maturity_date)
    expected_gross = yc.compound(bond.redemption_price, last_price)
    capital_gain = max(0.0, bond.redemption_price - last_price)
    expected_net_redemption = bond.redemption_price - capital_gain * (bond.tax_rate / 100)
    expected_net = yc.compound(expected_net_redemption, last_price)

    assert gross == pytest.approx(expected_gross)
    assert net == pytest.approx(expected_net)


def test_btp_yields_on_coupon_date_has_zero_accrued_interest() -> None:
    """Settling exactly on a coupon date: previous_coupon_date == today, so accrued
    interest is 0 and the outflow equals the clean price (no dirty-price premium)."""
    bond = _make_btp()  # annual coupons anchored on 1 July, today is 1 July
    last_price = 101.0

    gross, net = _calc_btp_yields(bond, last_price=last_price, today=TODAY)
    assert gross is not None and net is not None

    # Single remaining coupon (2027-07-01) + redemption at maturity, no accrued interest:
    # equivalent to a 2-effective-flow compound yield on (redemption + gross coupon).
    yc = YieldCalculator(TODAY, bond.maturity_date)
    expected_gross = yc.compound(bond.redemption_price + bond.nominal_rate, last_price)
    assert gross == pytest.approx(expected_gross)


def test_btp_yields_net_is_lower_than_gross() -> None:
    bond = _make_btp()
    gross, net = _calc_btp_yields(bond, last_price=98.0, today=TODAY)
    assert gross is not None and net is not None
    assert net < gross


def test_btp_yields_include_future_coupon_income() -> None:
    """At the same price, a bond with a positive coupon must yield strictly more
    than an otherwise-identical zero-coupon bond (pure price-appreciation only)."""
    last_price = 98.0
    with_coupon = _make_btp(nominal_rate=4.0, coupon_frequency=1)
    zero_coupon = _make_btp(nominal_rate=0.0, coupon_frequency=0)

    gross_with_coupon, _ = _calc_btp_yields(with_coupon, last_price=last_price, today=TODAY)
    gross_zero_coupon, _ = _calc_btp_yields(zero_coupon, last_price=last_price, today=TODAY)

    assert gross_with_coupon is not None and gross_zero_coupon is not None
    assert gross_with_coupon > gross_zero_coupon


# ------------------------------------------------------------------
# _calc_bond_yields — dispatch
# ------------------------------------------------------------------


def test_dispatch_btp_uses_btp_formula() -> None:
    bond = _make_btp()
    assert _calc_bond_yields(bond, last_price=98.0, today=TODAY) == _calc_btp_yields(
        bond, last_price=98.0, today=TODAY
    )


def test_dispatch_bot_uses_bot_formula() -> None:
    bond = _make_bot()
    assert _calc_bond_yields(bond, last_price=98.0, today=TODAY) == _calc_yields(
        bond, last_price=98.0, today=TODAY
    )
