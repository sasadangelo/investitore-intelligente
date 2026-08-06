# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for BondSyncService.

The network client and the underlying DB services are mocked so tests
are pure, fast, and DB-free.
"""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.services.bond_sync_service import BondSyncService

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TODAY = date.today()


def _make_bond(isin: str = "IT0005000001", issue_date: date | None = None) -> BondDTO:
    return BondDTO(
        name="BOT Test",
        isin=isin,
        bond_type="BOT",
        issue_date=issue_date or date(2025, 1, 15),
        maturity_date=date(2026, 1, 14),
        issue_price=98.5,
    )


def _make_quote(bond_id: int = 0) -> BondQuoteDTO:
    return BondQuoteDTO(bond_id=bond_id, last_price=98.5, date=TODAY, var_percent=0.1)


def _client_events(*events: dict[str, Any]):
    """Return a mock client whose fetch() yields the given events."""
    client = MagicMock()
    client.fetch.return_value = iter(events)
    return client


def _data_event(bond: BondDTO, quote: BondQuoteDTO, pct: int = 50) -> dict[str, Any]:
    return {"type": "data", "pct": pct, "message": bond.isin, "payload": (bond, quote)}


def _done_event(pct: int = 100) -> dict[str, Any]:
    return {"type": "done", "pct": pct, "message": "ok"}


def _error_event(msg: str = "network error") -> dict[str, Any]:
    return {"type": "error", "pct": 0, "message": msg}


# ------------------------------------------------------------------
# _upsert_bond: insert vs skip
# ------------------------------------------------------------------


def test_upsert_bond_creates_new_when_not_existing() -> None:
    svc = BondSyncService.__new__(BondSyncService)
    svc._bond_service = MagicMock()
    svc._quote_service = MagicMock()
    new_bond = _make_bond()
    svc._bond_service.get_by_isin.return_value = None
    svc._bond_service.create.return_value = new_bond.model_copy(update={"id": 1})

    result = svc._upsert_bond(new_bond)

    svc._bond_service.create.assert_called_once_with(new_bond)
    assert result.id == 1


def test_upsert_bond_returns_existing_unchanged() -> None:
    """If the bond already exists, it must be returned as-is — no update call."""
    svc = BondSyncService.__new__(BondSyncService)
    svc._bond_service = MagicMock()
    svc._quote_service = MagicMock()

    # Simulate a manually-corrected issue_date in DB
    existing = _make_bond(issue_date=date(2024, 12, 1)).model_copy(update={"id": 42})
    svc._bond_service.get_by_isin.return_value = existing

    # Client delivers a bond with a different (wrong) issue_date
    incoming = _make_bond(issue_date=date(2025, 1, 15))
    result = svc._upsert_bond(incoming)

    svc._bond_service.update.assert_not_called()
    svc._bond_service.create.assert_not_called()
    # The manually-corrected date is preserved
    assert result.issue_date == date(2024, 12, 1)
    assert result.id == 42


# ------------------------------------------------------------------
# sync: unknown source yields error event
# ------------------------------------------------------------------


def test_sync_unknown_source_yields_error() -> None:
    svc = BondSyncService()
    events = list(svc.sync("nonexistent_source"))
    assert len(events) == 1
    assert events[0]["type"] == "error"


# ------------------------------------------------------------------
# sync: client error event propagates
# ------------------------------------------------------------------


def test_sync_client_error_yields_error_event() -> None:
    client = _client_events(_error_event("timeout"))
    svc = BondSyncService.__new__(BondSyncService)
    svc._bond_service = MagicMock()
    svc._quote_service = MagicMock()

    with patch("intelligent_investor.services.bond_sync_service.ClientRegistry") as mock_reg:
        mock_reg.get.return_value = client
        events = list(svc.sync("any"))

    assert events[-1]["type"] == "error"
    assert "timeout" in events[-1]["message"]


# ------------------------------------------------------------------
# sync: happy path — new bond created, quote upserted
# ------------------------------------------------------------------


def test_sync_new_bond_is_created_and_quote_upserted() -> None:
    bond_in = _make_bond(isin="IT0005111111")
    quote_in = _make_quote()
    saved_bond = bond_in.model_copy(update={"id": 7})
    saved_quote = quote_in.model_copy(update={"bond_id": 7})

    client = _client_events(_data_event(bond_in, quote_in), _done_event())

    svc = BondSyncService.__new__(BondSyncService)
    svc._bond_service = MagicMock()
    svc._quote_service = MagicMock()
    svc._bond_service.get_by_isin.return_value = None
    svc._bond_service.create.return_value = saved_bond
    svc._quote_service.upsert.return_value = saved_quote

    with patch("intelligent_investor.services.bond_sync_service.ClientRegistry") as mock_reg:
        mock_reg.get.return_value = client
        events = list(svc.sync("any"))

    svc._bond_service.create.assert_called_once()
    svc._quote_service.upsert.assert_called_once()
    assert events[-1]["type"] == "done"
    assert "1" in events[-1]["message"]  # "1 BOT aggiornati"


# ------------------------------------------------------------------
# sync: existing bond — no update, only quote upserted
# ------------------------------------------------------------------


def test_sync_existing_bond_skips_update_updates_quote() -> None:
    existing = _make_bond(isin="IT0005222222", issue_date=date(2024, 12, 1)).model_copy(update={"id": 5})
    incoming_bond = _make_bond(isin="IT0005222222", issue_date=date(2025, 1, 15))
    quote_in = _make_quote()

    client = _client_events(_data_event(incoming_bond, quote_in), _done_event())

    svc = BondSyncService.__new__(BondSyncService)
    svc._bond_service = MagicMock()
    svc._quote_service = MagicMock()
    svc._bond_service.get_by_isin.return_value = existing
    svc._quote_service.upsert.return_value = quote_in.model_copy(update={"bond_id": 5})

    with patch("intelligent_investor.services.bond_sync_service.ClientRegistry") as mock_reg:
        mock_reg.get.return_value = client
        events = list(svc.sync("any"))

    svc._bond_service.update.assert_not_called()
    svc._bond_service.create.assert_not_called()
    svc._quote_service.upsert.assert_called_once()
    assert events[-1]["type"] == "done"
