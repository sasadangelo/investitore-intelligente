# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from collections.abc import Generator
from datetime import date, timedelta

import pytest
import sqlalchemy as sa

from intelligent_investor.dtos import BondDTO
from intelligent_investor.models.bond import BondDAO
from intelligent_investor.services import BondService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _id(dto: BondDTO) -> int:
    """Assert and return a saved DTO's id as non-None int."""
    assert dto.id is not None
    return dto.id


def _make_bond(
    name: str = "BTP 3.5 2030",
    isin: str = "IT0005000001",
    bond_type: str = "BTP",
    issue_date: date | None = None,
    maturity_date: date | None = None,
    issue_price: float = 99.0,
) -> BondDTO:
    today = date.today()
    return BondDTO(
        name=name,
        isin=isin,
        bond_type=bond_type,
        issue_date=issue_date or today - timedelta(days=365),
        maturity_date=maturity_date or today + timedelta(days=365),
        issue_price=issue_price,
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def service() -> BondService:
    return BondService()


@pytest.fixture(autouse=True)
def clean_bonds(test_engine: sa.Engine, service: BondService) -> Generator[None, None, None]:
    """Wipe the bonds table before and after every test."""
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(BondDAO))
    yield
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(BondDAO))


# ------------------------------------------------------------------
# create
# ------------------------------------------------------------------

def test_create_returns_dto_with_id(service: BondService) -> None:
    bond = _make_bond()
    saved = service.create(bond)
    assert saved.id is not None
    assert saved.isin == bond.isin


def test_create_duplicate_isin_raises(service: BondService) -> None:
    service.create(_make_bond())
    with pytest.raises(ValueError):
        service.create(_make_bond())


# ------------------------------------------------------------------
# get_by_id
# ------------------------------------------------------------------

def test_get_by_id_found(service: BondService) -> None:
    saved = service.create(_make_bond())
    fetched = service.get_by_id(_id(saved))
    assert fetched is not None
    assert fetched.isin == saved.isin


def test_get_by_id_not_found(service: BondService) -> None:
    assert service.get_by_id(99999) is None


# ------------------------------------------------------------------
# get_by_isin
# ------------------------------------------------------------------

def test_get_by_isin_found(service: BondService) -> None:
    saved = service.create(_make_bond(isin="IT0005999001"))
    fetched = service.get_by_isin("IT0005999001")
    assert fetched is not None
    assert fetched.id == _id(saved)


def test_get_by_isin_not_found(service: BondService) -> None:
    assert service.get_by_isin("NOTEXIST") is None


# ------------------------------------------------------------------
# list_all
# ------------------------------------------------------------------

def test_list_all_empty(service: BondService) -> None:
    assert service.list_all() == []


def test_list_all_returns_all(service: BondService) -> None:
    service.create(_make_bond(name="Bond A", isin="IT0001000001"))
    service.create(_make_bond(name="Bond B", isin="IT0001000002"))
    assert len(service.list_all()) == 2


# ------------------------------------------------------------------
# update
# ------------------------------------------------------------------

def test_update_changes_fields(service: BondService) -> None:
    saved = service.create(_make_bond(issue_price=99.0))
    updated_dto = BondDTO(
        id=saved.id,
        name=saved.name,
        isin=saved.isin,
        bond_type=saved.bond_type,
        issue_date=saved.issue_date,
        maturity_date=saved.maturity_date,
        issue_price=98.0,
    )
    result = service.update(updated_dto)
    assert result.issue_price == 98.0


def test_update_without_id_raises(service: BondService) -> None:
    with pytest.raises(ValueError):
        service.update(_make_bond())


def test_update_nonexistent_raises(service: BondService) -> None:
    bond = _make_bond().model_copy(update={"id": 99999})
    with pytest.raises(ValueError):
        service.update(bond)


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------

def test_delete_existing_returns_true(service: BondService) -> None:
    saved = service.create(_make_bond())
    assert service.delete(_id(saved)) is True
    assert service.get_by_id(_id(saved)) is None


def test_delete_nonexistent_returns_false(service: BondService) -> None:
    assert service.delete(99999) is False


# ------------------------------------------------------------------
# delete_expired
# ------------------------------------------------------------------

def test_delete_expired_removes_only_expired(service: BondService) -> None:
    today = date.today()
    service.create(_make_bond(
        name="Expired",
        isin="IT0009000001",
        issue_date=today - timedelta(days=400),
        maturity_date=today - timedelta(days=1),
    ))
    service.create(_make_bond(
        name="Active",
        isin="IT0009000002",
        issue_date=today - timedelta(days=100),
        maturity_date=today + timedelta(days=30),
    ))
    assert service.delete_expired() == 1
    remaining = service.list_all()
    assert len(remaining) == 1
    assert remaining[0].isin == "IT0009000002"
