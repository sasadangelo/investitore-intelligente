# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Teleborsa BOT scraper service.

Scrapes the full BOT list from https://www.teleborsa.it/Quotazioni/BOT,
then visits each detail page to collect issue date, issue price and
maturity date.  For every BOT found it upserts a BondDAO + BondQuoteDAO
row so the application DB stays in sync.

Progress is reported via ScraperEvent generator events so that the caller
(e.g. an SSE endpoint) can stream updates to the browser in real time.

Registration
------------
This module self-registers under the key "teleborsa_bot" at import time.
Just importing this module (or having it listed in services/__init__.py)
is enough to make it available via ScraperRegistry.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos import BondDTO, BondQuoteDTO
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_service import BondService
from intelligent_investor.services.scraper_base import (
    BaseScraper,
    ScraperEvent,
    ScraperRegistry,
)

logger = LoggerManager.get_logger("TeleborsaBotScraper")

_LIST_URL = "https://www.teleborsa.it/Quotazioni/BOT"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InvestitoreIntelligente/1.0; "
        "+https://github.com/sasadangelo/investitore-intelligente)"
    )
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(raw: str) -> float | None:
    """Convert a price string like '99,456' or '99.456' to float, or None."""
    cleaned = raw.strip().replace(",", ".").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(raw: str) -> date | None:
    """Parse dates in dd/mm/yyyy or yyyy-mm-dd format."""
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _detail_url_from_row(row_anchor) -> str | None:
    """Extract the absolute detail URL from a table row anchor tag."""
    if row_anchor is None:
        return None
    href = row_anchor.get("href", "")
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://www.teleborsa.it{href}"
    return None


def _scrape_detail(url: str) -> dict | None:
    """
    Fetch a single BOT detail page and extract all available fields:
        name, isin, last_price, var_percent,
        issue_date, issue_price, redemption_price, maturity_date

    Teleborsa renders data inside ``scheda-panel--body--data--item`` divs
    with a label|value structure.  The header block carries the name, ISIN,
    current price and daily change.

    Returns a dict with the extracted fields (only keys that were found are
    present), or None on HTTP/parse failure.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"Detail page request failed ({url}): {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    result: dict = {}

    # ── Header: name, ISIN, current price, daily change ─────────────────────
    header_title = soup.find(class_="scheda-panel--header--title")
    if header_title:
        # Text is "Bot Zc Apr27 A Eur|ISIN: IT0005704447 - Mercato: …"
        title_text = header_title.get_text(separator="|", strip=True)
        parts = title_text.split("|")
        result["name"] = parts[0].strip()
        isin_match = re.search(r"ISIN:\s*(IT\w{10})", title_text)
        if isin_match:
            result["isin"] = isin_match.group(1).upper()

    price_el = soup.find(class_="scheda-panel--header--data--price")
    if price_el:
        result["last_price"] = _parse_price(price_el.get_text(strip=True))

    change_el = soup.find(class_="scheda-panel--header--data--change")
    if change_el:
        result["var_percent"] = _parse_price(change_el.get_text(strip=True))

    # ── Body data items: label|value pairs ──────────────────────────────────
    for item in soup.find_all(class_="scheda-panel--body--data--item"):
        text = item.get_text(separator="|", strip=True)
        if "|" not in text:
            continue
        label, _, value = text.partition("|")
        label = label.strip().lower()
        value = value.strip()

        if label == "data emissione":
            result["issue_date"] = _parse_date(value)
        elif label == "prezzo emissione":
            result["issue_price"] = _parse_price(value)
        elif label == "prezzo rimborso":
            result["redemption_price"] = _parse_price(value)
        elif label == "scadenza":
            result["maturity_date"] = _parse_date(value)

    return result if result else None


# ---------------------------------------------------------------------------
# Scraper service
# ---------------------------------------------------------------------------

class TeleborsaBotScraper(BaseScraper):
    """
    Scrapes the Teleborsa BOT list + detail pages and upserts results into
    the application database.

    Emits ScraperEvent dicts:
        {"type": "progress", "pct": <0-100>, "message": "<step description>"}
        {"type": "done",     "pct": 100,     "message": "<summary>"}
        {"type": "error",    "pct": <last>,  "message": "<error description>"}
    """

    def __init__(self) -> None:
        self._bond_service = BondService()
        self._quote_service = BondQuoteService()

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def scrape(self) -> Generator[ScraperEvent, None, None]:
        # ── Step 1: fetch list page ──────────────────────────────────────
        yield ScraperEvent(type="progress", pct=5, message="Recupero lista BOT da Teleborsa…")

        try:
            resp = requests.get(_LIST_URL, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error(f"Failed to fetch BOT list: {exc}")
            yield ScraperEvent(type="error", pct=5, message=f"Errore nel recupero della lista: {exc}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if table is None:
            yield ScraperEvent(type="error", pct=5, message="Tabella BOT non trovata nella pagina.")
            return

        rows = table.find_all("tr")[1:]  # skip header
        rows = [r for r in rows if r.find_all("td")]
        total = len(rows)

        if total == 0:
            yield ScraperEvent(type="error", pct=5, message="Nessun BOT trovato nella tabella.")
            return

        yield ScraperEvent(type="progress", pct=10, message=f"Trovati {total} BOT. Avvio elaborazione…")

        # ── Step 2: process each row ─────────────────────────────────────
        ok = 0
        skipped = 0

        for idx, row in enumerate(rows):
            cols = row.find_all("td")
            if not cols:
                skipped += 1
                continue

            # Extract detail URL from the first column anchor
            anchor = cols[0].find("a")
            detail_url = _detail_url_from_row(anchor)

            # Fallback name from the list page (used in log messages before detail loads)
            raw_name = cols[0].get_text(strip=True).replace('"', "")

            # Compute progress: 10% reserved for list fetch, 90% shared across rows
            pct = 10 + int(90 * (idx + 1) / total)
            yield ScraperEvent(
                type="progress",
                pct=pct,
                message=f"[{idx + 1}/{total}] {raw_name}",
            )

            # Fetch detail page — all fields come from there
            detail = _scrape_detail(detail_url) if detail_url else None

            if detail is None:
                logger.warning(f"No detail data for '{raw_name}' — skipped")
                skipped += 1
                continue

            name            = detail.get("name") or raw_name
            isin            = detail.get("isin")
            last_price      = detail.get("last_price")
            var_pct         = detail.get("var_percent") or 0.0
            issue_date      = detail.get("issue_date")
            issue_price     = detail.get("issue_price")
            redemption_price = detail.get("redemption_price") or 100.0
            maturity_date   = detail.get("maturity_date")

            # Skip if any required field is missing
            if not (isin and last_price is not None and issue_date and issue_price and maturity_date):
                logger.warning(f"Incomplete data for '{name}' — skipped")
                skipped += 1
                continue

            # Narrow types after the guard above
            assert isinstance(isin, str)
            assert isinstance(last_price, float)
            assert isinstance(issue_date, date)
            assert isinstance(issue_price, float)
            assert isinstance(maturity_date, date)

            # Upsert Bond
            try:
                bond = self._bond_service.get_by_isin(isin)
                if bond is None:
                    bond = self._bond_service.create(BondDTO(
                        name=name,
                        isin=isin,
                        bond_type="BOT",
                        issue_date=issue_date,
                        maturity_date=maturity_date,
                        issue_price=issue_price,
                        redemption_price=redemption_price,
                        nominal_rate=0.0,
                        coupon_frequency=0,
                        tax_rate=12.5,
                    ))
                else:
                    # Refresh mutable fields in case Teleborsa updated them
                    bond = self._bond_service.update(BondDTO(
                        id=bond.id,
                        name=name,
                        isin=isin,
                        bond_type="BOT",
                        issue_date=issue_date,
                        maturity_date=maturity_date,
                        issue_price=issue_price,
                        redemption_price=redemption_price,
                        nominal_rate=bond.nominal_rate,
                        coupon_frequency=bond.coupon_frequency,
                        tax_rate=bond.tax_rate,
                    ))
            except Exception as exc:
                logger.error(f"Bond upsert failed for '{name}': {exc}")
                skipped += 1
                continue

            # After create/update the id is always populated
            assert bond.id is not None

            # Upsert Quote
            try:
                self._quote_service.upsert(BondQuoteDTO(
                    bond_id=bond.id,
                    date=date.today(),
                    last_price=last_price,
                    var_percent=var_pct,
                ))
                ok += 1
            except Exception as exc:
                logger.error(f"Quote upsert failed for bond id={bond.id}: {exc}")
                skipped += 1

        yield ScraperEvent(
            type="done",
            pct=100,
            message=f"Completato: {ok} BOT aggiornati, {skipped} ignorati.",
        )


# ---------------------------------------------------------------------------
# Self-registration
# ---------------------------------------------------------------------------

ScraperRegistry.register("teleborsa_bot", TeleborsaBotScraper)
