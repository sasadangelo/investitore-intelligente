# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from collections.abc import Generator
from datetime import date, timedelta

import pytest
import sqlalchemy as sa

from intelligent_investor.dtos import BondDTO, BondQuoteDTO
from intelligent_investor.models.bond import BondDAO
from intelligent_investor.models.bond_quotes import BondQuoteDAO
from intelligent_investor.services import BondQuoteService, BondService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _id(dto: BondDTO | BondQuoteDTO) -> int:
    """Assert and return a saved DTO's id as non-None int."""
    assert dto.id is not None
    return dto.id


def _make_bond(
    name: str = "BOT Zc 2025",
    isin: str = "IT0005000010",
    issue_date: date | None = None,
    maturity_date: date | None = None,
) -> BondDTO:
    today = date.today()
    return BondDTO(
        name=name,
        isin=isin,
        bond_type="BOT",
        issue_date=issue_date or today - timedelta(days=180),
        maturity_date=maturity_date or today + timedelta(days=180),
        issue_price=98.5,
    )


def _make_quote(bond_id: int, last_price: float = 99.1, var_percent: float = 0.05) -> BondQuoteDTO:
    return BondQuoteDTO(
        bond_id=bond_id,
        date=date.today(),
        last_price=last_price,
        var_percent=var_percent,
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def bond_service() -> BondService:
    return BondService()


@pytest.fixture(scope="module")
def service() -> BondQuoteService:
    return BondQuoteService()


@pytest.fixture(scope="module")
def parent_bond(bond_service: BondService, test_engine: sa.Engine) -> Generator[BondDTO, None, None]:
    """One bond shared across all tests in this module."""
    bond = bond_service.create(_make_bond())
    yield bond
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(BondDAO))


@pytest.fixture(autouse=True)
def clean_quotes(test_engine: sa.Engine) -> Generator[None, None, None]:
    """Wipe bond_quote table before and after every test."""
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(BondQuoteDAO))
    yield
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(BondQuoteDAO))


# ------------------------------------------------------------------
# create
# ------------------------------------------------------------------

def test_create_returns_dto_with_id(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.create(_make_quote(_id(parent_bond)))
    assert saved.id is not None
    assert saved.bond_id == _id(parent_bond)


def test_create_duplicate_bond_id_raises(service: BondQuoteService, parent_bond: BondDTO) -> None:
    service.create(_make_quote(_id(parent_bond)))
    with pytest.raises(ValueError):
        service.create(_make_quote(_id(parent_bond)))


# ------------------------------------------------------------------
# upsert
# ------------------------------------------------------------------

def test_upsert_inserts_when_absent(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.upsert(_make_quote(_id(parent_bond), last_price=99.0))
    assert saved.id is not None
    assert saved.last_price == 99.0


def test_upsert_replaces_existing(service: BondQuoteService, parent_bond: BondDTO) -> None:
    service.upsert(_make_quote(_id(parent_bond), last_price=99.0))
    updated = service.upsert(_make_quote(_id(parent_bond), last_price=99.9))
    assert updated.last_price == 99.9
    assert len(service.list_all()) == 1


# ------------------------------------------------------------------
# get_by_id
# ------------------------------------------------------------------

def test_get_by_id_found(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.create(_make_quote(_id(parent_bond)))
    fetched = service.get_by_id(_id(saved))
    assert fetched is not None
    assert fetched.id == _id(saved)


def test_get_by_id_not_found(service: BondQuoteService) -> None:
    assert service.get_by_id(99999) is None


# ------------------------------------------------------------------
# get_by_bond_id
# ------------------------------------------------------------------

def test_get_by_bond_id_found(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.create(_make_quote(_id(parent_bond)))
    fetched = service.get_by_bond_id(_id(parent_bond))
    assert fetched is not None
    assert fetched.id == _id(saved)


def test_get_by_bond_id_not_found(service: BondQuoteService) -> None:
    assert service.get_by_bond_id(99999) is None


# ------------------------------------------------------------------
# list_all
# ------------------------------------------------------------------

def test_list_all_empty(service: BondQuoteService) -> None:
    assert service.list_all() == []


def test_list_all_returns_all(service: BondQuoteService, parent_bond: BondDTO) -> None:
    service.create(_make_quote(_id(parent_bond)))
    assert len(service.list_all()) == 1


# ------------------------------------------------------------------
# update
# ------------------------------------------------------------------

def test_update_changes_price(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.create(_make_quote(_id(parent_bond), last_price=99.0))
    updated_dto = BondQuoteDTO(
        id=_id(saved),
        bond_id=saved.bond_id,
        date=saved.date,
        last_price=99.5,
        var_percent=0.10,
    )
    result = service.update(updated_dto)
    assert result.last_price == 99.5


def test_update_without_id_raises(service: BondQuoteService, parent_bond: BondDTO) -> None:
    with pytest.raises(ValueError):
        service.update(_make_quote(_id(parent_bond)))


def test_update_nonexistent_raises(service: BondQuoteService, parent_bond: BondDTO) -> None:
    dto = BondQuoteDTO(id=99999, bond_id=_id(parent_bond), date=date.today(), last_price=1.0, var_percent=0.0)
    with pytest.raises(ValueError):
        service.update(dto)


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------

def test_delete_existing_returns_true(service: BondQuoteService, parent_bond: BondDTO) -> None:
    saved = service.create(_make_quote(_id(parent_bond)))
    assert service.delete(_id(saved)) is True
    assert service.get_by_id(_id(saved)) is None


def test_delete_nonexistent_returns_false(service: BondQuoteService) -> None:
    assert service.delete(99999) is False


# ------------------------------------------------------------------
# delete_by_bond_id
# ------------------------------------------------------------------

def test_delete_by_bond_id_existing(service: BondQuoteService, parent_bond: BondDTO) -> None:
    service.create(_make_quote(_id(parent_bond)))
    assert service.delete_by_bond_id(_id(parent_bond)) is True
    assert service.get_by_bond_id(_id(parent_bond)) is None


def test_delete_by_bond_id_nonexistent(service: BondQuoteService) -> None:
    assert service.delete_by_bond_id(99999) is False
