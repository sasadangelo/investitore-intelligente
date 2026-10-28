# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
CRUD controller for bonds (list, detail, create, edit, delete).

This is the management side of the bond archive. The user-facing menu pages
built on top of it live in catalogue_controller and calculator_controller.
"""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from pydantic import ValidationError
from werkzeug.wrappers.response import Response

from intelligent_investor.dtos import BondDTO
from intelligent_investor.services import BondService
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_yields import bond_modified_duration, bond_yields

bond_bp = Blueprint("bonds", __name__, url_prefix="/bonds")

# Module-level singletons: services are stateless, so one instance serves every request
_service = BondService()
_quote_service = BondQuoteService()

# Bond types offered by the create/edit form dropdown: only BOTs and fixed-rate BTPs are handled
BOND_TYPES = ["BOT", "BTP"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    """Parse a date string in YYYY-MM-DD format (HTML date input)."""
    return date.fromisoformat(value)


def _form_to_dto(form: dict, bond_id: int | None = None) -> BondDTO:
    """
    Build a BondDTO from an HTML form dict.

    Optional numeric fields fall back to the defaults of a plain BOT: redemption at
    par, no coupon, 12.5% tax rate.

    Args:
        form: Submitted form fields
        bond_id: Id of the bond being updated, None on creation

    Returns:
        The bond DTO (not yet persisted)

    Raises:
        KeyError: if a required field is missing
        ValueError: if a date or number cannot be parsed
        ValidationError: if the bond data is inconsistent
    """
    url = form.get("auction_result_url", "").strip() or None
    first_coupon = form.get("first_coupon_date", "").strip()
    return BondDTO(
        id=bond_id,
        name=form["name"].strip(),
        isin=form["isin"].strip().upper(),  # ISINs are stored upper-case
        bond_type=form["bond_type"],
        issue_date=_parse_date(form["issue_date"]),
        maturity_date=_parse_date(form["maturity_date"]),
        first_coupon_date=_parse_date(first_coupon) if first_coupon else None,  # None = regular first date
        issue_price=float(form["issue_price"]),
        redemption_price=float(form.get("redemption_price", 100.0)),
        nominal_rate=float(form.get("nominal_rate", 0.0)),
        coupon_frequency=int(form.get("coupon_frequency", 0)),
        tax_rate=float(form.get("tax_rate", 12.5)),
        auction_result_url=url,  # None = use auto-computed URL
    )


def _render_form(bond: BondDTO | dict | None, action: str, title: str) -> str:
    """
    Render the create/edit form with the allowed bond types.

    Args:
        bond: Bond to pre-fill the form with: None for an empty form, a BondDTO when editing,
            or the submitted form dict when re-showing it after a validation error
        action: URL the form posts to
        title: Page and card title

    Returns:
        The rendered form page
    """
    return render_template("bonds/form.html", bond=bond, bond_types=BOND_TYPES, action=action, title=title)


def _not_found() -> Response:
    """Flash a "not found" warning and redirect to the bond list (shared by every route taking a bond id)."""
    flash("Obbligazione non trovata.", "warning")
    return redirect(url_for("bonds.index"))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bond_bp.route("/", methods=["GET"])
def index() -> str:
    """GET /bonds/ — list every bond in the archive, matured ones included, by maturity date."""
    # today is passed so the template can mark matured bonds
    bonds = sorted(_service.list_all(), key=lambda b: b.maturity_date)
    return render_template("bonds/index.html", bonds=bonds, today=date.today())


@bond_bp.route("/<int:bond_id>", methods=["GET"])
def detail(bond_id: int) -> str | Response:
    """GET /bonds/<id> — read-only view of a bond with its last quote and computed yields."""
    today = date.today()
    bond = _service.get_by_id(bond_id)
    if bond is None:
        return _not_found()

    # Yields are available only once the bond has a quote
    quote = _quote_service.get_by_bond_id(bond_id)
    gross_yield, net_yield = bond_yields(bond, quote.last_price, today) if quote else (None, None)
    modified_duration = bond_modified_duration(bond, net_yield, today)
    residual_days = (bond.maturity_date - today).days if bond.maturity_date >= today else 0
    total_days = (bond.maturity_date - bond.issue_date).days

    # Pro-rata issue discount (disaggio) still to accrue, and the tax due on it
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
        modified_duration=modified_duration,
        residual_days=residual_days,
        disaggio_lordo=disaggio_lordo,
        imposta_disaggio=imposta_disaggio,
    )


@bond_bp.route("/new", methods=["GET"])
def new() -> str:
    """GET /bonds/new — show the empty creation form."""
    return _render_form(bond=None, action=url_for("bonds.create"), title="Nuova obbligazione")


@bond_bp.route("/", methods=["POST"])
def create() -> Response | tuple[str, int]:
    """
    POST /bonds/ — persist a new bond from form data.

    On invalid input the form is shown again with the user's data, a flash message and status 422.
    """
    try:
        _service.create(_form_to_dto(request.form))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        return _render_form(bond=request.form, action=url_for("bonds.create"), title="Nuova obbligazione"), 422
    flash("Obbligazione creata con successo.", "success")
    return redirect(url_for("bonds.index"))


@bond_bp.route("/<int:bond_id>/edit", methods=["GET"])
def edit(bond_id: int) -> str | Response:
    """GET /bonds/<id>/edit — show the pre-filled edit form."""
    bond = _service.get_by_id(bond_id)
    if bond is None:
        return _not_found()
    return _render_form(bond=bond, action=url_for("bonds.update", bond_id=bond_id), title="Modifica obbligazione")


@bond_bp.route("/<int:bond_id>", methods=["POST"])
def update(bond_id: int) -> Response | tuple[str, int]:
    """
    POST /bonds/<id> — update an existing bond from form data.

    On invalid input the form is shown again with the user's data, a flash message and status 422.
    """
    if _service.get_by_id(bond_id) is None:
        return _not_found()
    try:
        _service.update(_form_to_dto(request.form, bond_id=bond_id))
    except (ValueError, ValidationError) as e:
        flash(f"Errore di validazione: {e}", "danger")
        action = url_for("bonds.update", bond_id=bond_id)
        return _render_form(bond=request.form, action=action, title="Modifica obbligazione"), 422
    flash("Obbligazione aggiornata con successo.", "success")
    return redirect(url_for("bonds.index"))


@bond_bp.route("/<int:bond_id>/delete", methods=["GET"])
def confirm_delete(bond_id: int) -> str | Response:
    """GET /bonds/<id>/delete — show the deletion confirmation page."""
    bond = _service.get_by_id(bond_id)
    if bond is None:
        return _not_found()
    return render_template("bonds/confirm_delete.html", bond=bond)


@bond_bp.route("/<int:bond_id>/delete", methods=["POST"])
def delete(bond_id: int) -> Response:
    """POST /bonds/<id>/delete — delete a bond (the confirmation page is the GET on the same URL)."""
    if not _service.delete(bond_id):
        return _not_found()
    flash("Obbligazione eliminata con successo.", "success")
    return redirect(url_for("bonds.index"))
