# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from collections.abc import Generator
from typing import Literal

import pytest
import sqlalchemy as sa

from intelligent_investor.dtos.bank_profile import BankCommissionDTO, BankProfileDTO
from intelligent_investor.models.bank_profile import BankCommissionDAO, BankProfileDAO
from intelligent_investor.services.bank_profile_service import BankProfileService

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_profile(
    bank_name: str = "Banca Test",
    profile_name: str = "Internet Banking",
    notes: str | None = None,
) -> BankProfileDTO:
    return BankProfileDTO(bank_name=bank_name, profile_name=profile_name, notes=notes)


def _make_commission(
    profile_id: int,
    venue: Literal["asta", "mot"] = "asta",
    duration_type: Literal["any", "annual", "semiannual", "quarterly"] = "any",
    days_min: int | None = None,
    days_max: int | None = None,
    commission_pct: float = 0.10,
    commission_min: float = 0.0,
    commission_max: float | None = None,
    commission_fixed: float = 0.0,
) -> BankCommissionDTO:
    return BankCommissionDTO(
        profile_id=profile_id,
        venue=venue,
        duration_type=duration_type,
        days_min=days_min,
        days_max=days_max,
        commission_pct=commission_pct,
        commission_min=commission_min,
        commission_max=commission_max,
        commission_fixed=commission_fixed,
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def service() -> BankProfileService:
    return BankProfileService()


@pytest.fixture(autouse=True)
def clean_tables(test_engine: sa.Engine) -> Generator[None, None, None]:
    """Wipe bank_commission and bank_profile before and after every test."""
    with test_engine.begin() as conn:
        conn.execute(sa.delete(table=BankCommissionDAO))
        conn.execute(sa.delete(table=BankProfileDAO))
    yield
    with test_engine.begin() as conn:
        conn.execute(sa.delete(table=BankCommissionDAO))
        conn.execute(sa.delete(table=BankProfileDAO))


# ------------------------------------------------------------------
# BankProfile CRUD
# ------------------------------------------------------------------


def test_create_profile_returns_dto_with_id(service: BankProfileService) -> None:
    saved: BankProfileDTO = service.create_profile(profile=_make_profile())
    assert saved.id is not None
    assert saved.bank_name == "Banca Test"
    assert saved.profile_name == "Internet Banking"


def test_get_profile_found(service: BankProfileService) -> None:
    saved: BankProfileDTO = service.create_profile(profile=_make_profile())
    assert saved.id is not None
    fetched: BankProfileDTO | None = service.get_profile(profile_id=saved.id)
    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.bank_name == saved.bank_name


def test_get_profile_not_found(service: BankProfileService) -> None:
    assert service.get_profile(profile_id=99999) is None


def test_list_profiles_empty(service: BankProfileService) -> None:
    assert service.list_profiles() == []


def test_list_profiles_returns_all_ordered(service: BankProfileService) -> None:
    service.create_profile(profile=_make_profile(bank_name="Zeta Bank", profile_name="Filiale"))
    service.create_profile(profile=_make_profile(bank_name="Alpha Bank", profile_name="Online"))
    profiles: list[BankProfileDTO] = service.list_profiles()
    assert len(profiles) == 2
    assert profiles[0].bank_name == "Alpha Bank"
    assert profiles[1].bank_name == "Zeta Bank"


def test_update_profile_changes_fields(service: BankProfileService) -> None:
    saved = service.create_profile(profile=_make_profile(notes=None))
    assert saved.id is not None
    updated: BankProfileDTO = BankProfileDTO(
        id=saved.id,
        bank_name=saved.bank_name,
        profile_name="Filiale",
        notes="aggiornato",
    )
    result = service.update_profile(updated)
    assert result.profile_name == "Filiale"
    assert result.notes == "aggiornato"


def test_update_profile_without_id_raises(service: BankProfileService) -> None:
    with pytest.raises(ValueError):
        service.update_profile(_make_profile())


def test_update_profile_nonexistent_raises(service: BankProfileService) -> None:
    ghost = BankProfileDTO(id=99999, bank_name="X", profile_name="Y")
    with pytest.raises(ValueError):
        service.update_profile(ghost)


def test_delete_profile_existing_returns_true(service: BankProfileService) -> None:
    saved = service.create_profile(_make_profile())
    assert saved.id is not None
    assert service.delete_profile(saved.id) is True
    assert service.get_profile(saved.id) is None


def test_delete_profile_nonexistent_returns_false(service: BankProfileService) -> None:
    assert service.delete_profile(99999) is False


# ------------------------------------------------------------------
# BankCommission CRUD
# ------------------------------------------------------------------


def test_create_commission_returns_dto_with_id(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    commission = service.create_commission(_make_commission(profile_id=profile.id))
    assert commission.id is not None
    assert commission.profile_id == profile.id
    assert commission.commission_pct == 0.10


def test_get_commission_found(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    saved = service.create_commission(_make_commission(profile_id=profile.id))
    assert saved.id is not None
    fetched = service.get_commission(saved.id)
    assert fetched is not None
    assert fetched.id == saved.id


def test_get_commission_not_found(service: BankProfileService) -> None:
    assert service.get_commission(99999) is None


def test_list_commissions_empty(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    assert service.list_commissions(profile.id) == []


def test_list_commissions_returns_rows_for_profile(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    service.create_commission(_make_commission(profile_id=profile.id, venue="asta"))
    service.create_commission(_make_commission(profile_id=profile.id, venue="mot"))
    rows = service.list_commissions(profile.id)
    assert len(rows) == 2


def test_update_commission_changes_fields(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    saved = service.create_commission(_make_commission(profile_id=profile.id, commission_pct=0.10))
    assert saved.id is not None
    updated = BankCommissionDTO(
        id=saved.id,
        profile_id=profile.id,
        venue="asta",
        commission_pct=0.15,
    )
    result = service.update_commission(updated)
    assert result.commission_pct == 0.15


def test_update_commission_without_id_raises(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    with pytest.raises(ValueError):
        service.update_commission(_make_commission(profile_id=profile.id))


def test_delete_commission_existing_returns_true(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    saved = service.create_commission(_make_commission(profile_id=profile.id))
    assert saved.id is not None
    assert service.delete_commission(saved.id) is True
    assert service.get_commission(saved.id) is None


def test_delete_commission_nonexistent_returns_false(service: BankProfileService) -> None:
    assert service.delete_commission(99999) is False


# ------------------------------------------------------------------
# resolve_commission — business logic critica
# ------------------------------------------------------------------


def test_resolve_commission_exact_days_range(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    # annual range: 271+ days
    service.create_commission(
        _make_commission(profile_id=profile.id, venue="asta", days_min=271, days_max=None, commission_pct=0.15)
    )
    # fallback any
    service.create_commission(
        _make_commission(profile_id=profile.id, venue="asta", days_min=None, days_max=None, commission_pct=0.03)
    )
    result = service.resolve_commission(profile.id, "asta", 300)
    assert result is not None
    assert result.commission_pct == 0.15


def test_resolve_commission_fallback_to_any(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    # solo riga "any"
    service.create_commission(
        _make_commission(profile_id=profile.id, venue="asta", days_min=None, days_max=None, commission_pct=0.05)
    )
    result = service.resolve_commission(profile.id, "asta", 90)
    assert result is not None
    assert result.commission_pct == 0.05


def test_resolve_commission_no_match_returns_none(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    # commissione per "mot", cerco "asta"
    service.create_commission(
        _make_commission(profile_id=profile.id, venue="mot", days_min=None, days_max=None, commission_pct=0.10)
    )
    result = service.resolve_commission(profile.id, "asta", 100)
    assert result is None


def test_resolve_commission_days_none_matches_any_row(service: BankProfileService) -> None:
    profile = service.create_profile(_make_profile())
    assert profile.id is not None
    service.create_commission(
        _make_commission(profile_id=profile.id, venue="asta", days_min=None, days_max=None, commission_pct=0.07)
    )
    result = service.resolve_commission(profile.id, "asta", None)
    assert result is not None
    assert result.commission_pct == 0.07
