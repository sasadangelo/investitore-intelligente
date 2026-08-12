# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Teleborsa BTP client.

Fetches and parses the full BTP list from https://www.teleborsa.it/Quotazioni/BTP,
then visits each detail page to collect all fields.

Only fixed-rate BTPs are synced (name contains "Fx", "Tf", "Green" or follows the
legacy "Btp-<day><mon><yy> <rate>" naming, and the detail page reports
"Tipo bond: Tasso Fisso"). Inflation-linked bonds (BTP€ i, "Btpi-...") and BTP
Italia are excluded even though Teleborsa also labels them "Tasso Fisso": their
real coupon is fixed but the paid cash flow is inflation-adjusted, which the
BondDTO.nominal_rate model cannot represent. Step-rate and zero-coupon BTPs
(Futura, Più, Valore, Coupon Strip, ...) are excluded via the "Tipo bond" field.

For every fixed-rate BTP found it yields a (BondDTO, BondQuoteDTO) pair as the
"data" event payload. Progress is reported via ClientEvent generator events so
that the caller (a service) can stream updates upstream in real time.

Registration
------------
This module self-registers under the key "teleborsa_btp" at import time.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from datetime import date, datetime
from re import Match

import requests
from bs4 import BeautifulSoup
from bs4._typing import _AtMostOneTag, _SomeTags
from bs4.element import Tag
from requests.models import Response

from intelligent_investor.clients.client_base import BaseClient, ClientEvent, ClientRegistry
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos import BondDTO, BondQuoteDTO

logger = LoggerManager.get_logger(name="TeleborsaBtpClient")

_LIST_URL = "https://www.teleborsa.it/Quotazioni/BTP"
_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; InvestitoreIntelligente/1.0; "
        "+https://github.com/sasadangelo/investitore-intelligente)"
    )
}

# Names starting with any of these prefixes are inflation-linked and must be
# excluded even though Teleborsa reports "Tipo bond: Tasso Fisso" for them.
_EXCLUDED_NAME_PREFIXES: tuple[str, ...] = ("btpi",)
_EXCLUDED_NAME_SUBSTRINGS: tuple[str, ...] = ("italia",)

_FIXED_RATE_BOND_TYPE = "tasso fisso"

_FREQUENCY_BY_LABEL: dict[str, int] = {
    "annuale": 1,
    "semestrale": 2,
    "trimestrale": 4,
    "mensile": 12,
}
_DEFAULT_COUPON_FREQUENCY = 2  # BTPs pay semi-annual coupons unless stated otherwise


# ---------------------------------------------------------------------------
# Private parse helpers
# ---------------------------------------------------------------------------


def _parse_price(raw: str) -> float | None:
    """Convert a price/rate string like '99,456' or '2.1%' to float, or None."""
    cleaned: str = raw.strip().replace(",", ".").replace("%", "").strip()
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


def _is_excluded_by_name(name: str) -> bool:
    """True for inflation-linked bonds that Teleborsa mislabels as 'Tasso Fisso'."""
    lowered = name.strip().lower()
    if lowered.startswith(_EXCLUDED_NAME_PREFIXES):
        return True
    return any(substr in lowered for substr in _EXCLUDED_NAME_SUBSTRINGS)


def _parse_rate_from_name(name: str) -> float | None:
    """Extract the nominal annual rate embedded in the bond name.

    Covers percent-based naming ('Btp Tf 0% Ag26 Eur', 'Btp Fx 2.1% Aug27 Eur',
    'Btpgreen 1,5%Ap45eur') and the legacy 'Btp-1Ag34 5' / 'Btp-1Fb33 5,75'
    style, where the rate is the last space-separated token with no '%' sign.
    """
    pct_match: Match[str] | None = re.search(r"(\d+[.,]?\d*)\s*%", name)
    if pct_match:
        return _parse_price(pct_match.group(1))
    parts: list[str] = name.strip().split()
    return _parse_price(parts[-1]) if parts else None


def _parse_coupon_frequency(raw: str | None) -> int:
    """Map the 'Frequenza cedola' label to a payments-per-year integer."""
    if raw is None:
        return _DEFAULT_COUPON_FREQUENCY
    return _FREQUENCY_BY_LABEL.get(raw.strip().lower(), _DEFAULT_COUPON_FREQUENCY)


def _detail_url(anchor) -> str | None:
    """Extract the absolute detail URL from a table-row anchor tag."""
    if anchor is None:
        return None
    href = anchor.get("href", "")
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://www.teleborsa.it{href}"
    return None


def _scrape_detail(url: str) -> dict | None:
    """
    Fetch a single BTP detail page and return a dict with:
        name, isin, last_price, var_percent, bond_type,
        issue_date, issue_price, redemption_price, maturity_date,
        coupon_frequency, annual_rate, current_coupon

    Returns None on HTTP or parse failure.
    """
    try:
        resp: Response = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"Detail page request failed ({url}): {exc}")
        return None

    soup: BeautifulSoup = BeautifulSoup(resp.text, "html.parser")
    result: dict = {}

    header_title: _AtMostOneTag = soup.find(class_="scheda-panel--header--title")
    if header_title:
        title_text: str = header_title.get_text(separator="|", strip=True)
        parts: list[str] = title_text.split(sep="|")
        result["name"] = parts[0].strip()
        isin_match: Match[str] | None = re.search(r"ISIN:\s*(IT\w{10})", title_text)
        if isin_match:
            result["isin"] = isin_match.group(1).upper()

    price_el: _AtMostOneTag = soup.find(class_="scheda-panel--header--data--price")
    if price_el:
        result["last_price"] = _parse_price(price_el.get_text(strip=True))

    change_el: _AtMostOneTag = soup.find(class_="scheda-panel--header--data--change")
    if change_el:
        result["var_percent"] = _parse_price(change_el.get_text(strip=True))

    for item in soup.find_all(class_="scheda-panel--body--data--item"):
        text = item.get_text(separator="|", strip=True)
        if "|" not in text:
            continue
        label, _, value = text.partition("|")
        label: str = label.strip().lower()
        value: str = value.strip()

        if label == "data emissione":
            result["issue_date"] = _parse_date(value)
        elif label == "prezzo emissione":
            result["issue_price"] = _parse_price(value)
        elif label == "prezzo rimborso":
            result["redemption_price"] = _parse_price(value)
        elif label == "scadenza":
            result["maturity_date"] = _parse_date(value)
        elif label == "tipo bond":
            result["bond_type"] = value
        elif label == "frequenza cedola":
            result["coupon_frequency"] = _parse_coupon_frequency(value)
        elif label == "cedola annuale" and value != "---":
            result["annual_rate"] = _parse_price(value)
        elif label == "cedola in corso" and value != "---":
            result["current_coupon"] = _parse_price(value)

    return result if result else None


def _resolve_nominal_rate(name: str, detail: dict) -> float | None:
    """Determine the annual nominal rate, preferring the most reliable source.

    Priority: 'Cedola annuale' (already annual) > 'Cedola in corso' scaled by
    coupon frequency (per-period value) > rate parsed from the bond name
    (always present, covers the legacy naming where neither field is filled).
    """
    annual_rate = detail.get("annual_rate")
    if annual_rate is not None:
        return annual_rate

    current_coupon = detail.get("current_coupon")
    if current_coupon is not None:
        frequency = detail.get("coupon_frequency", _DEFAULT_COUPON_FREQUENCY)
        return round(current_coupon * frequency, 6)

    return _parse_rate_from_name(name)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TeleborsaBtpClient(BaseClient):
    """
    Fetches all BTPs from Teleborsa and yields parsed (BondDTO, BondQuoteDTO)
    pairs as a "data" ClientEvent for each successfully parsed fixed-rate row.

    Event sequence per run:
        {"type": "progress", "pct": 5,   "message": "Recupero lista…"}
        {"type": "progress", "pct": 10,  "message": "Trovati N BTP…"}
        {"type": "progress", "pct": N,   "message": "[k/N] <name>"}   # one per row
        {"type": "data",     "pct": N,   "message": "<name>",
         "payload": (BondDTO, BondQuoteDTO)}                            # one per valid row
        {"type": "done",     "pct": 100, "message": "<summary>"}
        — or —
        {"type": "error",    "pct": N,   "message": "<reason>"}
    """

    def fetch(self) -> Generator[ClientEvent, None, None]:
        yield ClientEvent(type="progress", pct=5, message="Recupero lista BTP da Teleborsa…", payload=None)

        try:
            resp: Response = requests.get(url=_LIST_URL, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error(f"Failed to fetch BTP list: {exc}")
            yield ClientEvent(type="error", pct=5, message=f"Errore nel recupero della lista: {exc}", payload=None)
            return

        soup: BeautifulSoup = BeautifulSoup(resp.text, "html.parser")
        table: _AtMostOneTag = soup.find("table")
        if table is None:
            yield ClientEvent(type="error", pct=5, message="Tabella BTP non trovata nella pagina.", payload=None)
            return

        rows: list[Tag] = [r for r in table.find_all("tr")[1:] if r.find_all("td")]
        total: int = len(rows)

        if total == 0:
            yield ClientEvent(type="error", pct=5, message="Nessun BTP trovato nella tabella.", payload=None)
            return

        yield ClientEvent(type="progress", pct=10, message=f"Trovati {total} BTP. Avvio elaborazione…", payload=None)

        ok = 0
        skipped = 0

        for idx, row in enumerate(rows):
            cols: _SomeTags = row.find_all("td")
            anchor: _AtMostOneTag = cols[0].find("a")
            raw_name: str = cols[0].get_text(strip=True).replace('"', "")
            pct = 10 + int(90 * (idx + 1) / total)

            yield ClientEvent(type="progress", pct=pct, message=f"[{idx + 1}/{total}] {raw_name}", payload=None)

            if _is_excluded_by_name(raw_name):
                skipped += 1
                continue

            detail_url: str | None = _detail_url(anchor)
            detail = _scrape_detail(detail_url) if detail_url else None

            if detail is None:
                logger.warning(f"No detail data for '{raw_name}' — skipped")
                skipped += 1
                continue

            bond_type_label = (detail.get("bond_type") or "").strip().lower()
            if bond_type_label != _FIXED_RATE_BOND_TYPE:
                skipped += 1
                continue

            name = detail.get("name") or raw_name
            if _is_excluded_by_name(name):
                skipped += 1
                continue

            isin = detail.get("isin")
            last_price = detail.get("last_price")
            var_pct = detail.get("var_percent") or 0.0
            issue_date = detail.get("issue_date")
            issue_price = detail.get("issue_price")
            redemption_price = detail.get("redemption_price") or 100.0
            maturity_date = detail.get("maturity_date")
            coupon_frequency = detail.get("coupon_frequency", _DEFAULT_COUPON_FREQUENCY)
            nominal_rate = _resolve_nominal_rate(name, detail)

            if not (
                isin
                and last_price is not None
                and issue_date
                and issue_price
                and maturity_date
                and nominal_rate is not None
            ):
                logger.warning(f"Incomplete data for '{name}' — skipped")
                skipped += 1
                continue

            bond_dto: BondDTO = BondDTO(
                name=name,
                isin=isin,
                bond_type="BTP",
                issue_date=issue_date,
                maturity_date=maturity_date,
                issue_price=issue_price,
                redemption_price=redemption_price,
                nominal_rate=nominal_rate,
                coupon_frequency=coupon_frequency,
                tax_rate=12.5,
            )
            quote_dto: BondQuoteDTO = BondQuoteDTO(
                bond_id=0,  # bond_id is not known yet; the service will fill it in
                date=date.today(),
                last_price=last_price,
                var_percent=var_pct,
            )

            yield ClientEvent(type="data", pct=pct, message=name, payload=(bond_dto, quote_dto))
            ok += 1

        yield ClientEvent(
            type="done",
            pct=100,
            message=f"Fetch completato: {ok} BTP recuperati, {skipped} ignorati.",
            payload=None,
        )


# ---------------------------------------------------------------------------
# Self-registration
# ---------------------------------------------------------------------------

ClientRegistry.register(name="teleborsa_btp", client_class=TeleborsaBtpClient)
