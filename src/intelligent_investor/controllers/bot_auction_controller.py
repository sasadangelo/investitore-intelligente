# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from collections import defaultdict
from datetime import date
from itertools import groupby

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pydantic import ValidationError

from intelligent_investor.dtos.bot_auction import BotAuctionDTO
from intelligent_investor.services.bot_auction_service import BotAuctionService
from intelligent_investor.services.bot_forecast_service import BotForecastService

bot_auction_bp = Blueprint("auctions", __name__, url_prefix="/auctions")
_service = BotAuctionService()
_forecast_service = BotForecastService()

PERIOD_LABELS = {"mid_month": "Metà mese", "end_month": "Fine mese"}
DURATION_LABELS = {"annual": "Annuale", "semiannual": "Semestrale", "tbd": "t.b.d."}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_date_opt(value: str) -> date | None:
    return date.fromisoformat(value) if value and value.strip() else None


def _form_to_dto(form: dict, auction_id: int | None = None) -> BotAuctionDTO:
    """Build a BotAuctionDTO from an HTML form dict."""
    duration_type = form["duration_type"]
    maturity_raw = form.get("maturity_date", "").strip()
    return BotAuctionDTO(
        id=auction_id,
        period=form["period"],
        duration_type=duration_type,
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


@bot_auction_bp.route("/", methods=["GET"])
def index() -> str:
    """List upcoming BOT auctions grouped by month."""
    auctions = _service.list_upcoming()
    grouped = _group_by_month(auctions)
    return render_template(
        "auctions/index.html",
        grouped=grouped,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
    )


@bot_auction_bp.route("/new", methods=["GET"])
def new():
    """Show the empty creation form."""
    return render_template(
        "auctions/form.html",
        auction=None,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
        action=url_for("auctions.create"),
        title="Nuova Asta BOT",
    )


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
        return render_template(
            "auctions/form.html",
            auction=request.form,
            period_labels=PERIOD_LABELS,
            duration_labels=DURATION_LABELS,
            action=url_for("auctions.create"),
            title="Nuova Asta BOT",
        ), 422


@bot_auction_bp.route("/<int:auction_id>/edit", methods=["GET"])
def edit(auction_id: int):
    """Show the pre-filled edit form."""
    auction = _service.get_by_id(auction_id)
    if auction is None:
        flash("Asta non trovata.", "warning")
        return redirect(url_for("auctions.index"))
    return render_template(
        "auctions/form.html",
        auction=auction,
        period_labels=PERIOD_LABELS,
        duration_labels=DURATION_LABELS,
        action=url_for("auctions.update", auction_id=auction_id),
        title="Modifica Asta BOT",
    )


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
        return render_template(
            "auctions/form.html",
            auction=request.form,
            period_labels=PERIOD_LABELS,
            duration_labels=DURATION_LABELS,
            action=url_for("auctions.update", auction_id=auction_id),
            title="Modifica Asta BOT",
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
