# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for CatalogueService and sort_entries.

CatalogueService depends on BondService and BondQuoteService (both DB-backed).
We mock them so tests are pure, fast, and DB-free.
Covers:
  - list_entries: maturity filter, bond_type filter, quote pairing and yields, argument validation
  - list_entries with PurchaseCosts: commissions, minimum fee, bank profile, BOTs through the calculator
  - sort_entries: maturity / gross yield / net yield, entries without yield always last
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from intelligent_investor.dtos.bank_profile import BankCommissionDTO
from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.services.bond_yields import bond_yields
from intelligent_investor.services.catalogue_service import (
    CatalogueEntry,
    CatalogueService,
    PurchaseCosts,
    sort_entries,
)

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
    svc._bank_svc = MagicMock()
    svc._bank_svc.get_profile.return_value = None  # no profile: no fee per coupon
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


# ------------------------------------------------------------------
# list_entries with PurchaseCosts ("Parametri avanzati")
# ------------------------------------------------------------------


def _btp(id_: int, maturity_date: date) -> BondDTO:
    return _bond(id_, maturity_date).model_copy(update={"nominal_rate": 3.0, "coupon_frequency": 2})


def _bot(id_: int, maturity_date: date) -> BondDTO:
    return BondDTO(
        id=id_,
        name=f"BOT {id_}",
        isin=f"IT000500{id_:04d}",
        bond_type="BOT",
        issue_date=date(2026, 4, 1),
        maturity_date=maturity_date,
        issue_price=98.5,
    )


def _entries(costs: PurchaseCosts | None, bonds: list[BondDTO], prices: dict[int, float]) -> dict[int, CatalogueEntry]:
    svc = _service_with_mocks(bonds, [_quote(id_, price) for id_, price in prices.items()])
    return {e.bond.id: e for e in svc.list_entries(today=TODAY, costs=costs)}


def test_costs_add_net_gain_and_lower_the_net_yield() -> None:
    bonds, prices = [_btp(1, date(2030, 1, 1))], {1: 99.0}
    plain = _entries(None, bonds, prices)[1]
    costed = _entries(PurchaseCosts(face_value=10000, commission_pct=0.19, commission_min=5.0), bonds, prices)[1]

    assert plain.net_gain is None
    assert costed.net_gain is not None and costed.net_gain > 0
    assert costed.net_yield is not None and plain.net_yield is not None
    assert costed.net_yield < plain.net_yield
    assert costed.gross_yield == pytest.approx(plain.gross_yield)  # the gross yield has no costs


def test_commission_weighs_more_on_a_short_bond() -> None:
    # Same one-off commission, spread over 6 months or over 5 years
    bonds, prices = [_bot(1, date(2027, 1, 1)), _btp(2, date(2031, 7, 1))], {1: 98.8, 2: 99.0}
    no_fees = _entries(PurchaseCosts(face_value=10000), bonds, prices)
    fees = _entries(PurchaseCosts(face_value=10000, commission_pct=0.19), bonds, prices)

    short_drop = no_fees[1].net_yield - fees[1].net_yield  # type: ignore[operator]
    long_drop = no_fees[2].net_yield - fees[2].net_yield  # type: ignore[operator]
    assert short_drop == pytest.approx(0.34, abs=0.02)  # 0.19% over 184 days, compounded over a year
    assert long_drop < short_drop / 5


def test_minimum_commission_weighs_more_on_a_small_lot() -> None:
    bonds, prices = [_btp(1, date(2030, 1, 1))], {1: 99.0}
    costs = {"commission_pct": 0.19, "commission_min": 5.0}
    big = _entries(PurchaseCosts(face_value=10000, **costs), bonds, prices)[1]
    small = _entries(PurchaseCosts(face_value=1000, **costs), bonds, prices)[1]

    # 5 € minimum on 1,000 € is 0.5%, against 0.19% on 10,000 €
    assert small.net_yield < big.net_yield  # type: ignore[operator]


def test_bank_profile_commission_resolved_per_bond() -> None:
    bond = _btp(1, date(2030, 1, 1))
    svc = _service_with_mocks([bond], [_quote(1, 99.0)])
    svc._bank_svc.resolve_commission.return_value = BankCommissionDTO(
        profile_id=4, venue="mot", commission_pct=0.19, commission_min=2.95, commission_max=19.0
    )
    # Manual fields are ignored when a profile is chosen
    costs = PurchaseCosts(face_value=100000, bank_profile_id=4, commission_pct=5.0)

    with_profile = svc.list_entries(today=TODAY, costs=costs)[0]
    capped = _entries(PurchaseCosts(face_value=100000, commission_pct=0.19, commission_max=19.0), [bond], {1: 99.0})[1]

    # Tier looked up on the issue-to-maturity days, as the calculator page does
    svc._bank_svc.resolve_commission.assert_called_once_with(4, "mot", (bond.maturity_date - bond.issue_date).days)
    assert with_profile.net_gain == pytest.approx(capped.net_gain)  # 19 € cap, not 5%


def test_bank_profile_without_mot_row_means_no_commission() -> None:
    bond = _btp(1, date(2030, 1, 1))
    svc = _service_with_mocks([bond], [_quote(1, 99.0)])
    svc._bank_svc.resolve_commission.return_value = None

    with_profile = svc.list_entries(today=TODAY, costs=PurchaseCosts(face_value=10000, bank_profile_id=4))[0]
    free = _entries(PurchaseCosts(face_value=10000), [bond], {1: 99.0})[1]

    assert with_profile.net_gain == pytest.approx(free.net_gain)


def test_bot_with_costs_goes_through_the_calculator() -> None:
    # Without commissions the calculator differs from the indicative BOT formula only by
    # stamp duty and by when the discount tax is paid (at purchase, not at maturity)
    bot = _bot(1, date(2027, 4, 1))
    costed = _entries(PurchaseCosts(face_value=10000), [bot], {1: 98.9})[1]
    _, indicative_net = bond_yields(bot, 98.9, TODAY)

    assert costed.net_gain is not None
    assert costed.net_yield == pytest.approx(indicative_net - 0.2, abs=0.05)  # about 0.20%/year of stamp duty


def test_coupon_fee_from_the_bank_profile() -> None:
    bond = _btp(1, date(2030, 1, 1))
    svc = _service_with_mocks([bond], [_quote(1, 99.0)])
    svc._bank_svc.resolve_commission.return_value = None
    svc._bank_svc.get_profile.return_value = MagicMock(coupon_fee=2.0)
    # The manual fee is ignored when a profile is chosen
    costs = PurchaseCosts(face_value=10000, bank_profile_id=4, coupon_fee=9.0)
    with_profile = svc.list_entries(today=TODAY, costs=costs)[0]
    manual = _entries(PurchaseCosts(face_value=10000, coupon_fee=2.0), [bond], {1: 99.0})[1]
    free = _entries(PurchaseCosts(face_value=10000), [bond], {1: 99.0})[1]

    # 7 semi-annual coupons from 01/07/2026 (excluded) to 01/01/2030
    assert with_profile.net_gain == pytest.approx(manual.net_gain)
    assert manual.net_gain == pytest.approx(free.net_gain - 2.0 * 7)
