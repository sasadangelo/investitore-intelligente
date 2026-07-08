# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
import json
from collections.abc import Generator
from datetime import date

from flask import (Blueprint, Response, flash, redirect, render_template,
                   request, stream_with_context, url_for)
from flask.wrappers import Response
from pydantic import ValidationError

from intelligent_investor.dtos import BondDTO
from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.services import BondService, BondSyncService
from intelligent_investor.services.bond_quote_service import BondQuoteService

bond_bp = Blueprint("bonds", __name__, url_prefix="/bonds")
_service = BondService()
_quote_service = BondQuoteService()
_sync_service = BondSyncService()

# Allowed bond types for dropdowns
BOND_TYPES = ["BOT", "BTP", "BTP_ITALIA", "CORPORATE"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date:
    """Parse a date string in YYYY-MM-DD format (HTML date input)."""
    return date.fromisoformat(value)


def _calc_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """
    Compute gross and net annualised yield for a zero-coupon BOT.

        gross = (redemption / last_price) ^ (1 / yearfrac) - 1
        net   = ((redemption - imposta_disaggio) / last_price) ^ (1 / yearfrac) - 1

    where:
        giorni_totali    = (maturity - issue) in days
        giorni_residui   = (maturity - today) in days
        disaggio_lordo   = (redemption - issue_price) * giorni_residui / giorni_totali
        imposta_disaggio = disaggio_lordo * (tax_rate / 100)
        yearfrac         = giorni_residui / (366 if leap else 365)

    The net yield deducts the withholding tax from the redemption amount
    (i.e. the net cash received at maturity), not from the purchase price.

    Returns (gross_pct, net_pct) as percentage values, or (None, None) if the
    data is insufficient.
    """
    total_days = (bond.maturity_date - bond.issue_date).days
    residual_days = (bond.maturity_date - today).days

    if residual_days <= 0 or total_days <= 0 or last_price <= 0:
        return None, None

    year_days = 366 if _is_leap(bond.maturity_date.year) else 365
    yearfrac = residual_days / year_days

    disaggio_lordo   = (bond.redemption_price - bond.issue_price) * residual_days / total_days
    imposta_disaggio = disaggio_lordo * (bond.tax_rate / 100)

    gross = (bond.redemption_price / last_price) ** (1 / yearfrac) - 1
    net   = ((bond.redemption_price - imposta_disaggio) / last_price) ** (1 / yearfrac) - 1

    return gross * 100, net * 100


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _form_to_dto(form: dict, bond_id: int | None = None) -> BondDTO:
    """Build a BondDTO from an HTML form dict."""
    return BondDTO(
        id=bond_id,
        name=form["name"].strip(),
        isin=form["isin"].strip().upper(),
        bond_type=form["bond_type"],
        issue_date=_parse_date(form["issue_date"]),
        maturity_date=_parse_date(form["maturity_date"]),
        issue_price=float(form["issue_price"]),
        redemption_price=float(form.get("redemption_price", 100.0)),
        nominal_rate=float(form.get("nominal_rate", 0.0)),
        coupon_frequency=int(form.get("coupon_frequency", 0)),
        tax_rate=float(form.get("tax_rate", 12.5)),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bond_bp.route(rule="/", methods=["GET"])
def index() -> str:
    """List all bonds."""
    today: date = date.today()
    bonds: list[BondDTO] = sorted(
        (b for b in _service.list_all() if b.maturity_date >= today),
        key=lambda b: b.maturity_date,
    )
    quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in _quote_service.list_all()}

    # Pre-compute yields so the template doesn't need math operations
    yields: dict[int, tuple[float | None, float | None]] = {}
    for bond in bonds:
        if bond.id is not None:
            quote: BondQuoteDTO | None = quotes.get(bond.id)
            if quote is not None:
                yields[bond.id] = _calc_yields(bond=bond, last_price=quote.last_price, today=today)

    return render_template(template_name_or_list="bonds/index.html", bonds=bonds, quotes=quotes, yields=yields)


@bond_bp.route(rule="/refresh-bot-quotes/stream", methods=["GET"])
def refresh_bot_quotes_stream() -> Response:
    """
    SSE endpoint — streams bond sync progress events to the browser.

    Each event is a JSON-encoded SyncEvent:
        data: {"type": "progress"|"done"|"error", "pct": 0-100, "message": "..."}
    """
    def _event_stream() -> Generator[str, None, None]:
        try:
            for event in _sync_service.sync(source="teleborsa_bot"):
                yield f"data: {json.dumps(obj=event)}\n\n"
        except Exception as exc:
            error_event = {"type": "error", "pct": 0, "message": str(exc)}
            yield f"data: {json.dumps(obj=error_event)}\n\n"

    return Response(
        stream_with_context(generator_or_function=_event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering
        },
    )


@bond_bp.route("/<int:bond_id>", methods=["GET"])
def detail(bond_id: int):
    """Show the detail/read-only view of a bond with computed yields."""
    today = date.today()
    bond = _service.get_by_id(bond_id)
    if bond is None:
        flash("BOT non trovato.", "warning")
        return redirect(url_for("bonds.index"))

    quote = _quote_service.get_by_bond_id(bond_id)
    gross_yield, net_yield = (
        _calc_yields(bond, quote.last_price, today) if quote else (None, None)
    )
    residual_days = (bond.maturity_date - today).days if bond.maturity_date >= today else 0
    total_days = (bond.maturity_date - bond.issue_date).days

    disaggio_lordo = None
    imposta_disaggio = None
    if total_days > 0 and residual_days > 0:
        disaggio_lordo = (bond.redemption_price - bond.issue_price) * residual_days / total_days
        imposta_disaggio = disaggio_lordo * (bond.tax_rate / 100)

    return render_template(
        "bonds/detail.html",
        bond=bond,
        quote=quote,
        gross_yield=gross_yield,
        net_yield=net_yield,
        residual_days=residual_days,
        disaggio_lordo=disaggio_lordo,
        imposta_disaggio=imposta_disaggio,
    )


@bond_bp.route("/new", methods=["GET"])
def new():
    """Show the empty creation form."""
    return render_template(
        "bonds/form.html",
        bond=None,
        bond_types=BOND_TYPES,
        action=url_for("bonds.create"),
        title="Nuovo BOT",
    )


@bond_bp.route("/", methods=["POST"])
def create():
    """Persist a new bond from form data."""
    try:
        dto = _form_to_dto(request.form)
        _service.create(dto)
        flash("BOT creato con successo.", "success")
        return redirect(url_for("bonds.index"))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        return render_template(
            "bonds/form.html",
            bond=request.form,
            bond_types=BOND_TYPES,
            action=url_for("bonds.create"),
            title="Nuovo BOT",
        ), 422


@bond_bp.route("/<int:bond_id>/edit", methods=["GET"])
def edit(bond_id: int):
    """Show the pre-filled edit form."""
    bond = _service.get_by_id(bond_id)
    if bond is None:
        flash("BOT non trovato.", "warning")
        return redirect(url_for("bonds.index"))
    return render_template(
        "bonds/form.html",
        bond=bond,
        bond_types=BOND_TYPES,
        action=url_for("bonds.update", bond_id=bond_id),
        title="Modifica BOT",
    )


@bond_bp.route("/<int:bond_id>", methods=["POST"])
def update(bond_id: int):
    """Update an existing bond from form data."""
    existing = _service.get_by_id(bond_id)
    if existing is None:
        flash("BOT non trovato.", "warning")
        return redirect(url_for("bonds.index"))
    try:
        dto = _form_to_dto(request.form, bond_id=bond_id)
        _service.update(dto)
        flash("BOT aggiornato con successo.", "success")
        return redirect(url_for("bonds.index"))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        return render_template(
            "bonds/form.html",
            bond=request.form,
            bond_types=BOND_TYPES,
            action=url_for("bonds.update", bond_id=bond_id),
            title="Modifica BOT",
        ), 422


@bond_bp.route("/<int:bond_id>/delete", methods=["GET"])
def confirm_delete(bond_id: int):
    """Show deletion confirmation page."""
    bond = _service.get_by_id(bond_id)
    if bond is None:
        flash("BOT non trovato.", "warning")
        return redirect(url_for("bonds.index"))
    return render_template("bonds/confirm_delete.html", bond=bond)


@bond_bp.route("/<int:bond_id>/delete", methods=["POST"])
def delete(bond_id: int):
    """Delete a bond."""
    deleted = _service.delete(bond_id)
    if deleted:
        flash("BOT eliminato con successo.", "success")
    else:
        flash("BOT non trovato.", "warning")
    return redirect(url_for("bonds.index"))
