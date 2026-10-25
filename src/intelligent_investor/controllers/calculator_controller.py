# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Controller for the "Calcolatore" menu entry.

Lets the user simulate a BOT purchase (and optional sale) on a catalogue bond or
on a manually entered one, and renders the net result computed by
BondCalculatorService.
"""
import json
from datetime import date

from flask import Blueprint, flash, render_template, request
from pydantic import ValidationError
from werkzeug.datastructures import ImmutableMultiDict

from intelligent_investor.dtos import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services import BondService
from intelligent_investor.services.bank_profile_service import BankProfileService
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_calculator_service import BondCalculatorService

calculator_bp = Blueprint("calculator", __name__, url_prefix="/calculator")

# Module-level singletons: services are stateless, so one instance serves every request
_service = BondService()
_quote_service = BondQuoteService()
_bank_service = BankProfileService()
_calculator_service = BondCalculatorService()

# Sentinel bond_id used by the transaction DTO when the BOT is entered manually
# (a manual BOT is never persisted, so it has no real id; DB ids start from 1)
MANUAL_BOND_ID = 0

# Human-readable (Italian) labels for numeric form fields, used in validation messages so the
# user sees "Prezzo acquisto" instead of the internal field name
_FIELD_LABELS: dict[str, str] = {
    "purchase_price": "Prezzo acquisto",
    "face_value": "Lotto nominale",
    "buy_commission_pct": "Commissione acquisto %",
    "buy_commission_min": "Commissione acquisto min",
    "buy_commission_max": "Commissione acquisto max",
    "buy_commission_fixed": "Commissione acquisto fissa",
    "sale_price": "Prezzo vendita",
    "sell_commission_pct": "Commissione vendita %",
    "sell_commission_min": "Commissione vendita min",
    "sell_commission_max": "Commissione vendita max",
    "sell_commission_fixed": "Commissione vendita fissa",
    "portfolio_losses": "Minusvalenze",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    """Parse a date string in YYYY-MM-DD format (HTML date input)."""
    return date.fromisoformat(value)


def _render(
    bond: BondDTO | None,
    tx: ImmutableMultiDict[str, str] | None = None,
    result: object | None = None,
) -> str:
    """
    Render the calculator page with the shared context (selectable bonds, quotes, bank profiles).

    Args:
        bond: Bond pre-selected in the form, if any
        tx: Submitted form, echoed back to keep the user's input
        result: Calculation result to display, if any

    Returns:
        The rendered HTML page
    """
    # Only bonds not yet matured can be bought, nearest maturity first in the dropdown
    today: date = date.today()
    bonds: list[BondDTO] = sorted(
        (b for b in _service.list_all() if b.maturity_date >= today),
        key=lambda b: b.maturity_date,
    )
    # Last quotes, keyed by bond id: the page pre-fills the purchase price with them
    quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in _quote_service.list_all()}
    return render_template(
        "calculator/index.html",
        bonds=bonds,
        quotes=quotes,
        bond=bond,
        tx=tx,
        result=result,
        # Serialised for the page's JavaScript, which fills the commission fields when a bank is chosen
        bank_profiles_json=json.dumps(_bank_service.profiles_with_commissions_json()),
    )


def _manual_bond(form: ImmutableMultiDict[str, str]) -> BondDTO:
    """
    Build a transient BOT from the "manual_*" form fields.

    Used to simulate a BOT that is not in the archive (e.g. an upcoming auction).
    The bond is never persisted.

    Args:
        form: Submitted calculator form

    Returns:
        The manual BOT, with id=None

    Raises:
        KeyError: if a required field is missing
        ValueError: if a field cannot be parsed
    """
    return BondDTO(
        id=None,
        name="BOT Manuale",
        isin="N/D",
        bond_type="BOT",
        issue_date=_parse_date(form["manual_issue_date"]),
        maturity_date=_parse_date(form["manual_maturity_date"]),
        issue_price=float(form["manual_issue_price"]),
        redemption_price=float(form.get("manual_redemption_price") or 100.0),  # blank field -> par
        tax_rate=12.5,  # government bonds are taxed at the favourable 12.5% rate
    )


def _form_to_transaction(form: ImmutableMultiDict[str, str], bond_id: int) -> BondTransactionDTO:
    """
    Build a BondTransactionDTO from the calculator form.

    Blank numeric fields count as 0, except the maximum commissions, where blank
    means "no cap" (None). Sale fields are read only when "has_sale" is checked.

    Args:
        form: Submitted calculator form
        bond_id: Id of the selected bond, or MANUAL_BOND_ID

    Returns:
        The transaction to calculate

    Raises:
        ValueError: if a numeric field is not a valid number
        ValidationError: if the resulting transaction is inconsistent
    """

    def _f(field: str, default: str = "0") -> float:
        """Read *field* as a float (blank -> *default*), with an Italian error message on bad input."""
        raw = (form.get(field, default) or default).strip()
        try:
            return float(raw)
        except ValueError:
            label = _FIELD_LABELS.get(field, field)
            raise ValueError(f"Il campo «{label}» non è un numero valido (valore ricevuto: «{raw}»)")

    # An unchecked HTML checkbox is not sent at all; a checked one is sent as "on"
    has_sale = form.get("has_sale") == "on"
    sale_date = _parse_date(form["sale_date"]) if has_sale and form.get("sale_date") else None
    sale_price = _f("sale_price") if has_sale and form.get("sale_price") else None
    # Maximum commissions: read separately because blank means "no cap", not 0
    buy_max_raw = form.get("buy_commission_max", "").strip()
    sell_max_raw = form.get("sell_commission_max", "").strip()

    return BondTransactionDTO(
        bond_id=bond_id,
        purchase_venue=form["purchase_venue"],  # type: ignore[arg-type]  # value checked by the DTO
        purchase_date=_parse_date(form["purchase_date"]),
        purchase_price=_f("purchase_price"),
        face_value=_f("face_value"),
        buy_commission_pct=_f("buy_commission_pct"),
        buy_commission_min=_f("buy_commission_min"),
        buy_commission_max=float(buy_max_raw) if buy_max_raw else None,
        buy_commission_fixed=_f("buy_commission_fixed"),
        sale_date=sale_date,
        sale_price=sale_price,
        sell_commission_pct=_f("sell_commission_pct"),
        sell_commission_min=_f("sell_commission_min"),
        sell_commission_max=float(sell_max_raw) if sell_max_raw else None,
        sell_commission_fixed=_f("sell_commission_fixed"),
        stamp_duty_period=form.get("stamp_duty_period", "quarterly"),  # type: ignore[arg-type]  # checked by the DTO
        portfolio_losses=_f("portfolio_losses"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@calculator_bp.route("/", methods=["GET"])
def index() -> str:
    """
    GET /calculator/ — show the empty calculator form.

    An optional ?bond_id=<id> pre-selects a specific bond (used when coming from
    the bond detail page); otherwise the bond with the nearest maturity is used.

    Returns:
        The rendered calculator page, without a result
    """
    preselect_id: int | None = request.args.get("bond_id", type=int)
    if preselect_id is not None:
        return _render(bond=_service.get_by_id(preselect_id))
    today: date = date.today()
    active = [b for b in _service.list_all() if b.maturity_date >= today]
    return _render(bond=min(active, key=lambda b: b.maturity_date) if active else None)


@calculator_bp.route("/", methods=["POST"])
def compute() -> str | tuple[str, int]:
    """
    POST /calculator/ — run the calculator on the submitted form and render the result.

    The form field bond_id is either a bond id from the archive or "manual", in which
    case the BOT data is read from the "manual_*" fields. On any input error the page
    is rendered again with the user's input and a flash message, and status 422.

    Returns:
        The rendered calculator page with the result, or (page, 422) on invalid input
    """
    form = request.form
    bond_id_raw = form.get("bond_id", "").strip()
    if not bond_id_raw:
        flash("Seleziona un BOT.", "warning")
        return _render(bond=None, tx=form), 422

    # Resolve the bond: either entered manually or loaded from the catalogue
    bond: BondDTO | None
    if bond_id_raw == "manual":
        try:
            bond = _manual_bond(form)
        except (KeyError, ValueError) as e:
            flash(f"Dati BOT manuale non validi: {e}", "danger")
            return _render(bond=None, tx=form), 422
        bond_id = MANUAL_BOND_ID
    else:
        bond_id = int(bond_id_raw)
        bond = _service.get_by_id(bond_id)
        if bond is None:
            flash("BOT non trovato.", "warning")
            return _render(bond=None, tx=form), 422

    # Build the transaction and calculate. ValidationError is caught first because
    # Pydantic's ValidationError is itself a subclass of ValueError.
    try:
        tx = _form_to_transaction(form, bond_id)
        result = _calculator_service.calculate(tx, bond)
    except ValidationError as e:
        # Show only the first human-readable Pydantic error message
        msg = e.errors()[0].get("msg", str(e)).removeprefix("Value error, ")
        flash(f"Errore: {msg}", "danger")
        return _render(bond=bond, tx=form), 422
    except ValueError as e:
        # Raised by _f() or _parse_date() with an already readable message
        flash(f"Errore nei parametri: {e}", "danger")
        return _render(bond=bond, tx=form), 422

    return _render(bond=bond, tx=form, result=result)
