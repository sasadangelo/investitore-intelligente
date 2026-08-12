# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the bond catalogue yield/sorting/pagination helpers in bond_controller.py.

Pure functions — no DB, no Flask request context, no I/O.
Covers:
  - _calc_btp_yields: coupon-schedule + multi-flow XIRR yield-to-maturity estimate
  - _calc_bond_yields: dispatch to the BTP vs BOT formula by bond_type
  - _sort_bonds / _toggle_sort_dir / _paginate: catalogue sorting and pagination (Fase 5)
"""

from datetime import date

import pytest

from intelligent_investor.controllers.bond_controller import (
    _calc_bond_yields,
    _calc_btp_yields,
    _calc_yields,
    _paginate,
    _sort_bonds,
    _toggle_sort_dir,
)
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
    assert _calc_bond_yields(bond, last_price=98.0, today=TODAY) == _calc_btp_yields(bond, last_price=98.0, today=TODAY)


def test_dispatch_bot_uses_bot_formula() -> None:
    bond = _make_bot()
    assert _calc_bond_yields(bond, last_price=98.0, today=TODAY) == _calc_yields(bond, last_price=98.0, today=TODAY)


# ------------------------------------------------------------------
# _sort_bonds / _toggle_sort_dir / _paginate — catalogue sorting & pagination
# ------------------------------------------------------------------


def _bond(id_: int, maturity_date: date) -> BondDTO:
    return BondDTO(
        id=id_,
        name=f"Bond {id_}",
        isin=f"IT000500{id_:04d}",
        bond_type="BTP",
        issue_date=date(2020, 1, 1),
        maturity_date=maturity_date,
        issue_price=99.0,
    )


def test_sort_bonds_by_maturity_ascending_default() -> None:
    b1, b2, b3 = _bond(1, date(2028, 1, 1)), _bond(2, date(2026, 1, 1)), _bond(3, date(2027, 1, 1))
    result = _sort_bonds([b1, b2, b3], yields={}, sort="maturity", direction="asc")
    assert [b.id for b in result] == [2, 3, 1]


def test_sort_bonds_by_maturity_descending() -> None:
    b1, b2, b3 = _bond(1, date(2028, 1, 1)), _bond(2, date(2026, 1, 1)), _bond(3, date(2027, 1, 1))
    result = _sort_bonds([b1, b2, b3], yields={}, sort="maturity", direction="desc")
    assert [b.id for b in result] == [1, 3, 2]


def test_sort_bonds_by_yield_gross_missing_values_sort_last() -> None:
    b1 = _bond(1, date(2026, 1, 1))  # no quote -> no yield
    b2 = _bond(2, date(2027, 1, 1))  # gross 3.0
    b3 = _bond(3, date(2028, 1, 1))  # gross 5.0
    yields = {2: (3.0, 2.5), 3: (5.0, 4.5)}

    result_desc = _sort_bonds([b1, b2, b3], yields, sort="yield_gross", direction="desc")
    assert [b.id for b in result_desc] == [3, 2, 1]

    result_asc = _sort_bonds([b1, b2, b3], yields, sort="yield_gross", direction="asc")
    assert [b.id for b in result_asc] == [2, 3, 1]


def test_sort_bonds_by_yield_net_uses_second_tuple_element() -> None:
    b1 = _bond(1, date(2027, 1, 1))
    b2 = _bond(2, date(2028, 1, 1))
    # b1 has the higher gross but lower net yield than b2
    yields = {1: (5.0, 2.0), 2: (4.0, 3.0)}

    result = _sort_bonds([b1, b2], yields, sort="yield_net", direction="desc")
    assert [b.id for b in result] == [2, 1]


def test_toggle_sort_dir_flips_when_same_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "maturity") == "desc"
    assert _toggle_sort_dir("maturity", "desc", "maturity") == "asc"


def test_toggle_sort_dir_uses_field_default_when_switching_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "yield_gross") == "desc"
    assert _toggle_sort_dir("yield_gross", "desc", "maturity") == "asc"


def test_paginate_slices_and_reports_total_pages() -> None:
    items = [_bond(i, date(2026, 1, 1)) for i in range(25)]
    page_items, page, total_pages = _paginate(items, page=2, per_page=10)
    assert [b.id for b in page_items] == list(range(10, 20))
    assert page == 2
    assert total_pages == 3


def test_paginate_clamps_page_above_range() -> None:
    items = [_bond(i, date(2026, 1, 1)) for i in range(5)]
    page_items, page, total_pages = _paginate(items, page=99, per_page=10)
    assert page == 1
    assert total_pages == 1
    assert [b.id for b in page_items] == [0, 1, 2, 3, 4]


def test_paginate_clamps_page_below_range() -> None:
    items = [_bond(i, date(2026, 1, 1)) for i in range(5)]
    page_items, page, total_pages = _paginate(items, page=0, per_page=10)
    assert page == 1
    assert [b.id for b in page_items] == [0, 1, 2, 3, 4]


def test_paginate_empty_list_returns_single_empty_page() -> None:
    page_items, page, total_pages = _paginate([], page=1, per_page=20)
    assert page_items == []
    assert page == 1
    assert total_pages == 1
