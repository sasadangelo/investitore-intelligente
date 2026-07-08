# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Bond synchronisation service.

Orchestrates a full sync cycle:
    1. Calls a network client (e.g. TeleborsaBotClient) to fetch remote data.
    2. For every (BondDTO, BondQuoteDTO) pair delivered by the client, upserts
       the Bond and its current Quote in the database via BondService and
       BondQuoteService.
    3. Streams SyncEvent progress dicts so that the caller (controller/SSE
       endpoint) can forward real-time updates to the browser.

Responsibility model
--------------------
  Controller  ──triggers──►  BondSyncService  ──calls──►  <Client>  (network)
                                    │
                                    └──upserts via──►  BondService / BondQuoteService  (DB)
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import TypedDict, cast

from intelligent_investor.clients.client_base import ClientRegistry
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos import BondDTO, BondQuoteDTO
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_service import BondService

logger = LoggerManager.get_logger("BondSyncService")


# ---------------------------------------------------------------------------
# Event type (forwarded upstream to the controller / SSE layer)
# ---------------------------------------------------------------------------

class SyncEvent(TypedDict):
    """
    A single progress or status event emitted during a sync run.

    type    : "progress" | "done" | "error"
    pct     : integer 0-100
    message : human-readable description
    """
    type: str
    pct: int
    message: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class BondSyncService:
    """
    Drives a complete bond synchronisation cycle for a named data source.

    Usage::

        for event in BondSyncService().sync("teleborsa_bot"):
            # event: SyncEvent
            ...
    """

    def __init__(self) -> None:
        self._bond_service = BondService()
        self._quote_service = BondQuoteService()

    def sync(self, source: str) -> Generator[SyncEvent, None, None]:
        """
        Run a full sync against the registered client identified by *source*.

        Yields SyncEvent dicts.  The final event has type "done" or "error".
        """
        logger.info(f"Starting bond sync from source='{source}'")
        ok = 0
        skipped = 0
        last_pct = 0
        # Initialised here so the post-loop check is always safe even if the
        # client generator yields nothing.
        last_event_type = "done"
        last_event_message = ""

        try:
            client = ClientRegistry.get(source)
        except KeyError as exc:
            yield SyncEvent(type="error", pct=0, message=str(exc))
            return

        for event in client.fetch():
            last_pct = event["pct"]

            if event["type"] == "progress":
                yield SyncEvent(type="progress", pct=last_pct, message=event["message"])

            elif event["type"] == "data":
                bond_dto, quote_dto = cast(tuple[BondDTO, BondQuoteDTO], event["payload"])
                name = event["message"]

                try:
                    bond = self._upsert_bond(bond_dto)
                except Exception as exc:
                    logger.error(f"Bond upsert failed for '{name}': {exc}")
                    skipped += 1
                    continue

                assert bond.id is not None, f"Bond id is None after upsert for ISIN={bond.isin}"

                try:
                    self._upsert_quote(quote_dto, bond_id=bond.id)
                    ok += 1
                except Exception as exc:
                    logger.error(f"Quote upsert failed for bond id={bond.id}: {exc}")
                    skipped += 1

            elif event["type"] in ("done", "error"):
                # Terminal event from the client — capture it and stop
                last_event_type = event["type"]
                last_event_message = event["message"]
                break

        if last_event_type == "error":
            yield SyncEvent(type="error", pct=last_pct, message=last_event_message)
        else:
            yield SyncEvent(
                type="done",
                pct=100,
                message=f"Sincronizzazione completata: {ok} BOT aggiornati, {skipped} ignorati.",
            )

        logger.info(f"Bond sync done: ok={ok}, skipped={skipped}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upsert_bond(self, dto: BondDTO) -> BondDTO:
        """Create or update a Bond record; returns the saved DTO with id."""
        existing = self._bond_service.get_by_isin(dto.isin)
        if existing is None:
            return self._bond_service.create(dto)
        # Refresh mutable fields; preserve fiscal fields from the existing record
        return self._bond_service.update(BondDTO(
            id=existing.id,
            name=dto.name,
            isin=dto.isin,
            bond_type=dto.bond_type,
            issue_date=dto.issue_date,
            maturity_date=dto.maturity_date,
            issue_price=dto.issue_price,
            redemption_price=dto.redemption_price,
            nominal_rate=existing.nominal_rate,
            coupon_frequency=existing.coupon_frequency,
            tax_rate=existing.tax_rate,
        ))

    def _upsert_quote(self, dto: BondQuoteDTO, bond_id: int) -> BondQuoteDTO:
        """Upsert the current quote for the given bond_id."""
        return self._quote_service.upsert(BondQuoteDTO(
            bond_id=bond_id,
            date=date.today(),
            last_price=dto.last_price,
            var_percent=dto.var_percent,
        ))
