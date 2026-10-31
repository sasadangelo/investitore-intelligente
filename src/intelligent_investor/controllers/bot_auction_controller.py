# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Controller for the "Aste" menu entry: the auction calendar (BOT and BTP auctions),
the bonds offered at BTP auctions and the BOT issue-price forecast.
"""
from collections import defaultdict
from datetime import date
from itertools import groupby

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pydantic import ValidationError

from intelligent_investor.dtos.bot_auction import SHORT_SESSION_PERIOD, AuctionOfferingDTO, BotAuctionDTO
from intelligent_investor.services import BondService
from intelligent_investor.services.bot_auction_service import BotAuctionService
from intelligent_investor.services.bot_forecast_service import BotForecastService

bot_auction_bp = Blueprint("auctions", __name__, url_prefix="/auctions")
_service = BotAuctionService()
_forecast_service = BotForecastService()
_bond_service = BondService()

PERIOD_LABELS = {"mid_month": "Metà mese", "end_month": "Fine mese"}
DURATION_LABELS = {"annual": "Annuale", "semiannual": "Semestrale", "tbd": "t.b.d."}
# MEF auction sessions, also the values of the ?session= filter of the calendar
SESSION_LABELS = {"bot": "BOT", "medium_long": "BTP medio-lungo", "short": "BTP Short"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_date_opt(value: str) -> date | None:
    return date.fromisoformat(value) if value and value.strip() else None


def _form_to_dto(form: dict, auction_id: int | None = None) -> BotAuctionDTO:
    """
    Build a BotAuctionDTO from an HTML form dict.

    For a BTP session the BOT-only fields are not read: there is no duration or
    maturity (the bonds offered carry them), and a BTP Short auction is always at
    month end.
    """
    session = form.get("session", "bot")
    is_bot = session == "bot"
    maturity_raw = form.get("maturity_date", "").strip() if is_bot else ""
    return BotAuctionDTO(
        id=auction_id,
        session=session,
        period=SHORT_SESSION_PERIOD if session == "short" else form["period"],
        duration_type=form["duration_type"] if is_bot else "tbd",
        announcement_date=_parse_date(form["announcement_date"]),
        submission_deadline=_parse_date(form["submission_deadline"]),
        auction_date=_parse_date(form["auction_date"]),
        settlement_date=_parse_date(form["settlement_date"]),
        maturity_date=_parse_date_opt(maturity_raw),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

MONTH_NAMES_IT = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre",
}


def _group_by_month(auctions):
    """Return list of (month_label, [auctions]) ordered by settlement_date."""
    groups = []
    for key, group in groupby(auctions, key=lambda a: (a.settlement_date.year, a.settlement_date.month)):
        year, month = key
        label = f"{MONTH_NAMES_IT[month]} {year}"
        groups.append((label, list(group)))
    return groups


@bot_auction_bp.route("/forecast", methods=["GET"])
def forecast() -> str:
    """Show issue-price forecasts for upcoming BOT auctions."""
    results = _forecast_service.forecast_all()
    return render_template(
        "auctions/forecast.html",
        results=results,
        duration_labels=DURATION_LABELS,
    )


def _render_form(auction, action: str, title: str, offerings: list[AuctionOfferingDTO] | None = None) -> str:
    """Render the auction form; offerings are shown only when editing a BTP auction."""
    return render_template(
        "auctions/form.html",
        auction=auction,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
        session_labels=SESSION_LABELS,
        offerings=offerings,
        action=action,
        title=title,
    )


@bot_auction_bp.route("/", methods=["GET"])
def index() -> str:
    """
    List upcoming auctions grouped by month, optionally only one session (?session=).

    BTP auctions show the bonds offered; one already in the catalogue (a reopening)
    links to its page and to the calculator set for that auction.
    """
    session = request.args.get("session") or None
    if session not in SESSION_LABELS:
        session = None
    auctions = [a for a in _service.list_upcoming() if session is None or a.session == session]
    offerings = _service.list_offerings([a.id for a in auctions if a.id is not None])
    bond_ids_by_isin = {b.isin: b.id for b in _bond_service.list_all()}
    return render_template(
        "auctions/index.html",
        grouped=_group_by_month(auctions),
        offerings=offerings,
        bond_ids_by_isin=bond_ids_by_isin,
        session_filter=session,
        session_labels=SESSION_LABELS,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
    )


@bot_auction_bp.route("/new", methods=["GET"])
def new():
    """Show the empty creation form."""
    return _render_form(None, url_for("auctions.create"), "Nuova asta")


@bot_auction_bp.route("/", methods=["POST"])
def create():
    """Persist a new auction entry from form data."""
    try:
        dto = _form_to_dto(request.form)
        _service.create(dto)
        flash("Asta creata con successo.", "success")
        return redirect(url_for("auctions.index"))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        return _render_form(request.form, url_for("auctions.create"), "Nuova asta"), 422


@bot_auction_bp.route("/<int:auction_id>/edit", methods=["GET"])
def edit(auction_id: int):
    """Show the pre-filled edit form."""
    auction = _service.get_by_id(auction_id)
    if auction is None:
        flash("Asta non trovata.", "warning")
        return redirect(url_for("auctions.index"))
    offerings = _service.list_offerings([auction_id]).get(auction_id, [])
    return _render_form(auction, url_for("auctions.update", auction_id=auction_id), "Modifica asta", offerings)


@bot_auction_bp.route("/<int:auction_id>", methods=["POST"])
def update(auction_id: int):
    """Update an existing auction entry from form data."""
    existing = _service.get_by_id(auction_id)
    if existing is None:
        flash("Asta non trovata.", "warning")
        return redirect(url_for("auctions.index"))
    try:
        dto = _form_to_dto(request.form, auction_id=auction_id)
        _service.update(dto)
        flash("Asta aggiornata con successo.", "success")
        return redirect(url_for("auctions.index"))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        offerings = _service.list_offerings([auction_id]).get(auction_id, [])
        return _render_form(
            request.form, url_for("auctions.update", auction_id=auction_id), "Modifica asta", offerings
        ), 422


@bot_auction_bp.route("/<int:auction_id>/delete", methods=["GET"])
def confirm_delete(auction_id: int):
    """Show deletion confirmation page."""
    auction = _service.get_by_id(auction_id)
    if auction is None:
        flash("Asta non trovata.", "warning")
        return redirect(url_for("auctions.index"))
    return render_template(
        "auctions/confirm_delete.html",
        auction=auction,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
        session_labels=SESSION_LABELS,
    )


@bot_auction_bp.route("/<int:auction_id>/delete", methods=["POST"])
def delete(auction_id: int):
    """Delete an auction entry."""
    deleted = _service.delete(auction_id)
    if deleted:
        flash("Asta eliminata con successo.", "success")
    else:
        flash("Asta non trovata.", "warning")
    return redirect(url_for("auctions.index"))


@bot_auction_bp.route("/<int:auction_id>/offerings", methods=["POST"])
def add_offering(auction_id: int):
    """
    Add a bond offered at a BTP auction.

    With just the ISIN of a bond already in the catalogue (a reopening) name and
    maturity are taken from it; a new bond needs at least the name.
    """
    auction = _service.get_by_id(auction_id)
    if auction is None or auction.session == "bot":
        flash("Asta BTP non trovata.", "warning")
        return redirect(url_for("auctions.index"))
    isin = request.form.get("isin", "").strip().upper()
    name = request.form.get("name", "").strip()
    maturity = _parse_date_opt(request.form.get("maturity_date", ""))
    bond = _bond_service.get_by_isin(isin) if isin else None
    if bond is not None:
        name = name or bond.name
        maturity = maturity or bond.maturity_date
    try:
        _service.add_offering(AuctionOfferingDTO(auction_id=auction_id, isin=isin, name=name, maturity_date=maturity))
        flash(f"Titolo {isin} aggiunto all'asta.", "success")
    except (ValueError, ValidationError):
        flash("Titolo non valido: serve un ISIN di 12 caratteri e, se il titolo non è in catalogo, il nome.", "danger")
    return redirect(url_for("auctions.edit", auction_id=auction_id))


@bot_auction_bp.route("/<int:auction_id>/offerings/<int:offering_id>/delete", methods=["POST"])
def delete_offering(auction_id: int, offering_id: int):
    """Remove a bond from a BTP auction."""
    if _service.delete_offering(offering_id):
        flash("Titolo tolto dall'asta.", "success")
    return redirect(url_for("auctions.edit", auction_id=auction_id))
