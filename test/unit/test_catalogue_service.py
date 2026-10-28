# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for CatalogueService and sort_entries.

CatalogueService depends on BondService and BondQuoteService (both DB-backed).
We mock them so tests are pure, fast, and DB-free.
Covers:
  - list_entries: maturity filter, bond_type filter, quote pairing, yields and duration, argument validation
  - sort_entries: maturity / gross yield / net yield, entries without yield always last
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.services.catalogue_service import CatalogueEntry, CatalogueService, sort_entries

TODAY = date(2026, 7, 1)


def _bond(id_: int, maturity_date: date, bond_type: str = "BTP") -> BondDTO:
    return BondDTO(
        id=id_,
        name=f"Bond {id_}",
        isin=f"IT000500{id_:04d}",
        bond_type=bond_type,
        issue_date=date(2020, 1, 1),
        maturity_date=maturity_date,
        issue_price=99.0,
    )


def _quote(bond_id: int, last_price: float) -> BondQuoteDTO:
    return BondQuoteDTO(bond_id=bond_id, date=TODAY, last_price=last_price, var_percent=0.0)


def _entry(id_: int, maturity_date: date, gross: float | None = None, net: float | None = None) -> CatalogueEntry:
    return CatalogueEntry(bond=_bond(id_, maturity_date), gross_yield=gross, net_yield=net)


def _service_with_mocks(bonds: list[BondDTO], quotes: list[BondQuoteDTO]) -> CatalogueService:
    svc = CatalogueService.__new__(CatalogueService)
    svc._bond_svc = MagicMock()
    svc._quote_svc = MagicMock()
    svc._bond_svc.list_all.return_value = bonds
    svc._quote_svc.list_all.return_value = quotes
    return svc


# ------------------------------------------------------------------
# list_entries
# ------------------------------------------------------------------


def test_list_entries_excludes_matured_bonds() -> None:
    matured = _bond(1, date(2026, 6, 30))
    maturing_today = _bond(2, TODAY)
    active = _bond(3, date(2027, 1, 1))
    svc = _service_with_mocks([matured, maturing_today, active], [])

    entries = svc.list_entries(today=TODAY)

    assert [e.bond.id for e in entries] == [2, 3]


def test_list_entries_filters_by_bond_type() -> None:
    bot = _bond(1, date(2027, 1, 1), bond_type="BOT")
    btp = _bond(2, date(2028, 1, 1), bond_type="BTP")
    svc = _service_with_mocks([bot, btp], [])

    assert [e.bond.id for e in svc.list_entries(bond_type="BOT", today=TODAY)] == [1]
    assert [e.bond.id for e in svc.list_entries(bond_type=None, today=TODAY)] == [1, 2]


def test_list_entries_pairs_quotes_and_computes_yields() -> None:
    quoted = _bond(1, date(2028, 1, 1))
    unquoted = _bond(2, date(2029, 1, 1))
    svc = _service_with_mocks([quoted, unquoted], [_quote(1, 98.0)])

    by_id = {e.bond.id: e for e in svc.list_entries(today=TODAY)}

    assert by_id[1].quote is not None and by_id[1].quote.last_price == 98.0
    assert by_id[1].gross_yield is not None and by_id[1].net_yield is not None
    assert by_id[2].quote is None
    assert by_id[2].gross_yield is None and by_id[2].net_yield is None


def test_list_entries_computes_duration_for_coupon_bonds_only() -> None:
    btp = _bond(1, date(2029, 7, 1)).model_copy(update={"nominal_rate": 3.35, "coupon_frequency": 2})
    bot = _bond(2, date(2027, 1, 1), bond_type="BOT")
    short_btp = _bond(3, date(2027, 6, 1)).model_copy(update={"nominal_rate": 3.0, "coupon_frequency": 2})
    svc = _service_with_mocks([btp, bot, short_btp], [_quote(1, 99.18), _quote(2, 98.0), _quote(3, 99.5)])

    by_id = {e.bond.id: e for e in svc.list_entries(today=TODAY)}

    assert by_id[1].modified_duration == pytest.approx(2.8, abs=0.1)
    assert by_id[2].modified_duration is None  # BOT: no coupons
    assert by_id[3].modified_duration is None  # less than 365 days to maturity (cell K16)


@pytest.mark.parametrize("sort, direction", [("name", "asc"), ("maturity", "up")])
def test_list_entries_rejects_unsupported_sort(sort: str, direction: str) -> None:
    svc = _service_with_mocks([], [])
    with pytest.raises(ValueError):
        svc.list_entries(sort=sort, direction=direction, today=TODAY)


# ------------------------------------------------------------------
# sort_entries
# ------------------------------------------------------------------


def test_sort_entries_by_maturity_ascending() -> None:
    entries = [_entry(1, date(2028, 1, 1)), _entry(2, date(2026, 1, 1)), _entry(3, date(2027, 1, 1))]
    assert [e.bond.id for e in sort_entries(entries, "maturity", "asc")] == [2, 3, 1]


def test_sort_entries_by_maturity_descending() -> None:
    entries = [_entry(1, date(2028, 1, 1)), _entry(2, date(2026, 1, 1)), _entry(3, date(2027, 1, 1))]
    assert [e.bond.id for e in sort_entries(entries, "maturity", "desc")] == [1, 3, 2]


def test_sort_entries_by_yield_gross_missing_values_sort_last() -> None:
    entries = [
        _entry(1, date(2026, 1, 1)),  # no quote -> no yield
        _entry(2, date(2027, 1, 1), gross=3.0, net=2.5),
        _entry(3, date(2028, 1, 1), gross=5.0, net=4.5),
    ]
    assert [e.bond.id for e in sort_entries(entries, "yield_gross", "desc")] == [3, 2, 1]
    assert [e.bond.id for e in sort_entries(entries, "yield_gross", "asc")] == [2, 3, 1]


def test_sort_entries_by_yield_net_uses_net_yield() -> None:
    # Entry 1 has the higher gross but lower net yield than entry 2
    entries = [_entry(1, date(2027, 1, 1), gross=5.0, net=2.0), _entry(2, date(2028, 1, 1), gross=4.0, net=3.0)]
    assert [e.bond.id for e in sort_entries(entries, "yield_net", "desc")] == [2, 1]
