# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pydantic import ValidationError

from intelligent_investor.dtos import BondDTO
from intelligent_investor.services import BondService

bond_bp = Blueprint("bonds", __name__, url_prefix="/bonds")
_service = BondService()

# Allowed bond types for dropdowns
BOND_TYPES = ["BOT", "BTP", "BTP_ITALIA", "CORPORATE"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date:
    """Parse a date string in YYYY-MM-DD format (HTML date input)."""
    return date.fromisoformat(value)


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

@bond_bp.route("/", methods=["GET"])
def index():
    """List all bonds."""
    bonds = _service.list_all()
    return render_template("bonds/index.html", bonds=bonds)


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
