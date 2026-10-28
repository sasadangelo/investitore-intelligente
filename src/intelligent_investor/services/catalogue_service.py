# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Bond catalogue service.

The catalogue is the set of bonds still on the market (not yet matured), each
paired with its last MOT quote and the indicative gross/net yield and modified
duration implied by it.
Entries can be filtered by bond type and sorted by maturity or yield.
"""
from dataclasses import dataclass
from datetime import date

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_service import BondService
from intelligent_investor.services.bond_yields import bond_modified_duration, bond_yields

logger = LoggerManager.get_logger("CatalogueService")

# Supported sort keys: maturity date, gross yield, net yield
SORT_FIELDS: tuple[str, ...] = ("maturity", "yield_gross", "yield_net")


@dataclass
class CatalogueEntry:
    """A catalogue row: a bond with its last quote and the yields implied by it."""

    bond: BondDTO
    quote: BondQuoteDTO | None = None  # None until the first quote sync
    gross_yield: float | None = None  # percentage, None when not computable
    net_yield: float | None = None  # percentage, None when not computable
    modified_duration: float | None = None  # None for BOTs and when not computable


class CatalogueService:
    """Builds the bond catalogue from the bond archive and the latest quotes."""

    def __init__(self) -> None:
        # Data sources; tests replace them with mocks
        self._bond_svc = BondService()
        self._quote_svc = BondQuoteService()

    def list_entries(
        self,
        bond_type: str | None = None,
        sort: str = "maturity",
        direction: str = "asc",
        today: date | None = None,
    ) -> list[CatalogueEntry]:
        """
        Return the catalogue entries, filtered and sorted.

        Args:
            bond_type: Only include bonds of this type; None for all types
            sort: One of SORT_FIELDS
            direction: "asc" or "desc"
            today: Valuation date (default: today); bonds maturing before it are excluded

        Returns:
            The sorted catalogue entries

        Raises:
            ValueError: if sort or direction is not supported
        """
        if sort not in SORT_FIELDS:
            raise ValueError(f"Unsupported sort field: {sort!r}")
        if direction not in ("asc", "desc"):
            raise ValueError(f"Unsupported sort direction: {direction!r}")

        # today is a parameter so tests can use a fixed date
        today = today or date.today()
        logger.info(f"Listing catalogue entries (bond_type={bond_type}, sort={sort} {direction})")

        # One query for all quotes instead of one per bond; each bond has at most one quote
        quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in self._quote_svc.list_all()}
        entries = [
            self._build_entry(bond, quotes.get(bond.id) if bond.id is not None else None, today)
            for bond in self._bond_svc.list_all()
            # A bond maturing today is still listed
            if bond.maturity_date >= today and (bond_type is None or bond.bond_type == bond_type)
        ]
        return sort_entries(entries, sort, direction)

    @staticmethod
    def _build_entry(bond: BondDTO, quote: BondQuoteDTO | None, today: date) -> CatalogueEntry:
        """
        Pair a bond with its quote and compute the yields implied by the quote, if any.

        Args:
            bond: Bond to wrap
            quote: Its last quote, or None if it was never synced
            today: Valuation date for the yields

        Returns:
            The catalogue entry; yields and duration stay None without a quote
        """
        if quote is None:
            return CatalogueEntry(bond=bond)
        gross, net = bond_yields(bond=bond, last_price=quote.last_price, today=today)
        return CatalogueEntry(
            bond=bond,
            quote=quote,
            gross_yield=gross,
            net_yield=net,
            modified_duration=bond_modified_duration(bond=bond, net_yield=net, today=today),
        )


def sort_entries(entries: list[CatalogueEntry], sort: str, direction: str) -> list[CatalogueEntry]:
    """
    Sort catalogue entries by maturity date, gross yield or net yield.

    When sorting by yield, entries without a computed value (no quote yet) always
    sort last — regardless of direction — since there is no meaningful position for
    them relative to a numeric yield. They are kept in maturity order among themselves.

    Args:
        entries: Entries to sort
        sort: One of SORT_FIELDS
        direction: "asc" or "desc"

    Returns:
        A new sorted list
    """
    reverse = direction == "desc"
    if sort == "maturity":
        return sorted(entries, key=lambda e: e.bond.maturity_date, reverse=reverse)

    def yield_value(e: CatalogueEntry) -> float | None:
        """The yield the entries are sorted by (gross or net), None if not computable."""
        return e.gross_yield if sort == "yield_gross" else e.net_yield

    with_yield = [e for e in entries if yield_value(e) is not None]
    without_yield = [e for e in entries if yield_value(e) is None]
    with_yield.sort(key=yield_value, reverse=reverse)  # type: ignore[arg-type]  # None filtered out above
    without_yield.sort(key=lambda e: e.bond.maturity_date)
    return with_yield + without_yield
