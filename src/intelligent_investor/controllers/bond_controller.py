# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
import json
from collections.abc import Generator
from datetime import date

from flask import Blueprint, Response, flash, redirect, render_template, request, stream_with_context, url_for
from pydantic import ValidationError

from intelligent_investor.dtos import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.dtos.bot_transaction import BotTransactionDTO
from intelligent_investor.services import BondService, BondSyncService
from intelligent_investor.services.bank_profile_service import BankProfileService
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bot_calculator_service import BotCalculatorService
from intelligent_investor.utils.coupon_schedule import CouponSchedule
from intelligent_investor.utils.yield_calculator import YieldCalculator, xirr

bond_bp = Blueprint("bonds", __name__, url_prefix="/bonds")
_service = BondService()
_quote_service = BondQuoteService()
_sync_service = BondSyncService()
_bank_service = BankProfileService()
_calculator_service = BotCalculatorService()

# Allowed bond types for dropdowns
BOND_TYPES = ["BOT", "BTP", "BTP_ITALIA", "CORPORATE"]

# Catalogue filter options (value, label) — restricted to the types actually in use for now
CATALOG_FILTERS: list[tuple[str, str]] = [("BOT", "BOT"), ("BTP", "BTP Tasso Fisso")]

# Catalogue sorting/pagination
SORT_FIELDS: tuple[str, ...] = ("maturity", "yield_gross", "yield_net")
SORT_DEFAULT_DIR: dict[str, str] = {"maturity": "asc", "yield_gross": "desc", "yield_net": "desc"}
# Index into the (gross, net) yield tuple for each sortable yield field
_YIELD_TUPLE_INDEX: dict[str, int] = {"yield_gross": 0, "yield_net": 1}
PER_PAGE_OPTIONS: tuple[int, ...] = (10, 20, 50, 100)
DEFAULT_PER_PAGE = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    """Parse a date string in YYYY-MM-DD format (HTML date input)."""
    return date.fromisoformat(value)


def _calc_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """Compute gross and net annualised compound yield for a zero-coupon BOT.

    Uses YieldCalculator with ACT_ACT (YEARFRAC basis 1), qty=1:
        gross = compound(redemption_price, last_price)
        net   = compound(redemption_price - imposta_disaggio, last_price)

    Returns (gross_pct, net_pct) as percentage values, or (None, None) if the
    data is insufficient.
    """
    total_days = (bond.maturity_date - bond.issue_date).days
    residual_days = (bond.maturity_date - today).days

    if residual_days <= 0 or total_days <= 0 or last_price <= 0:
        return None, None

    disaggio_lordo = (bond.redemption_price - bond.issue_price) * residual_days / total_days
    imposta_disaggio = disaggio_lordo * (bond.tax_rate / 100)

    yc = YieldCalculator(today, bond.maturity_date)
    gross = yc.compound(bond.redemption_price, last_price)
    net = yc.compound(bond.redemption_price - imposta_disaggio, last_price)

    return gross, net


def _calc_btp_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """Compute an indicative gross/net yield-to-maturity for a fixed-rate BTP.

    Uses the coupon schedule (Fase 1) and multi-flow XIRR (Fase 2) on the residual
    cash flows from today to maturity:
        outflow today = -(last_price + rateo lordo)         (corso secco / dirty price)
        inflows       = future gross/net coupons + redemption_price at maturity

    Net additionally deducts an indicative capital-gain tax on the clean-price gap
    (redemption_price - last_price), mirroring BtpCalculatorService's simplified
    capital-gain treatment. Commissions and stamp duty are not modelled here (unknown
    at catalogue level), same simplification already applied to the BOT catalogue yield.

    Returns (gross_pct, net_pct) as percentage values, or (None, None) if the bond
    has already matured or the quote is invalid.
    """
    if bond.maturity_date <= today or last_price <= 0:
        return None, None

    cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency, bond.nominal_rate, bond.tax_rate)
    dirty_price = last_price + cs.accrued_interest(today)
    future_coupons = [cp for cp in cs.schedule if cp.payment_date > today]

    capital_gain = max(0.0, bond.redemption_price - last_price)
    net_redemption = bond.redemption_price - capital_gain * (bond.tax_rate / 100)

    gross_cashflows: list[tuple[date, float]] = (
        [(today, -dirty_price)]
        + [(cp.payment_date, cp.gross_amount) for cp in future_coupons]
        + [(bond.maturity_date, bond.redemption_price)]
    )
    net_cashflows: list[tuple[date, float]] = (
        [(today, -dirty_price)]
        + [(cp.payment_date, cp.net_amount) for cp in future_coupons]
        + [(bond.maturity_date, net_redemption)]
    )

    try:
        return xirr(gross_cashflows), xirr(net_cashflows)
    except ValueError:
        return None, None


def _calc_bond_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """Dispatch to the yield formula matching the bond's type (catalogue-wide helper)."""
    if bond.bond_type == "BTP":
        return _calc_btp_yields(bond=bond, last_price=last_price, today=today)
    return _calc_yields(bond=bond, last_price=last_price, today=today)


def _sort_bonds(
    bonds: list[BondDTO],
    yields: dict[int, tuple[float | None, float | None]],
    sort: str,
    direction: str,
) -> list[BondDTO]:
    """Sort catalogue bonds by maturity date, gross yield or net yield.

    When sorting by yield, bonds without a computed value (no MOT quote yet) always
    sort last — regardless of direction — since there is no meaningful position for
    them relative to a numeric yield.
    """
    reverse = direction == "desc"
    if sort in _YIELD_TUPLE_INDEX:
        idx = _YIELD_TUPLE_INDEX[sort]

        def yield_value(b: BondDTO) -> float | None:
            return yields.get(b.id, (None, None))[idx] if b.id is not None else None

        with_yield = [b for b in bonds if yield_value(b) is not None]
        without_yield = [b for b in bonds if yield_value(b) is None]
        with_yield.sort(key=yield_value, reverse=reverse)  # type: ignore[arg-type]
        without_yield.sort(key=lambda b: b.maturity_date)
        return with_yield + without_yield
    return sorted(bonds, key=lambda b: b.maturity_date, reverse=reverse)


def _toggle_sort_dir(current_sort: str, current_dir: str, field: str) -> str:
    """Return the direction that clicking the *field* column header should switch to."""
    if current_sort == field:
        return "desc" if current_dir == "asc" else "asc"
    return SORT_DEFAULT_DIR[field]


def _paginate(items: list[BondDTO], page: int, per_page: int) -> tuple[list[BondDTO], int, int]:
    """Slice *items* to the given 1-indexed *page*. Returns (page_items, clamped_page, total_pages)."""
    total_pages = max(1, -(-len(items) // per_page))  # ceil division
    page = min(max(1, page), total_pages)
    start = (page - 1) * per_page
    return items[start : start + per_page], page, total_pages


def _form_to_dto(form: dict, bond_id: int | None = None) -> BondDTO:
    """Build a BondDTO from an HTML form dict."""
    url = form.get("auction_result_url", "").strip() or None
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
        auction_result_url=url,  # None = use auto-computed URL
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bond_bp.route(rule="/", methods=["GET"])
def index() -> str:
    """
    List all bonds, optionally filtered by ?bond_type=BOT|BTP (see CATALOG_FILTERS).

    Supports sorting via ?sort=maturity|yield_gross|yield_net&dir=asc|desc (default:
    maturity ascending) and pagination via ?page=&per_page= (per_page restricted to
    PER_PAGE_OPTIONS, default DEFAULT_PER_PAGE).
    """
    today: date = date.today()
    bond_type_filter: str | None = request.args.get("bond_type") or None

    sort = request.args.get("sort", "maturity")
    if sort not in SORT_FIELDS:
        sort = "maturity"
    direction = request.args.get("dir") or SORT_DEFAULT_DIR[sort]
    if direction not in ("asc", "desc"):
        direction = SORT_DEFAULT_DIR[sort]
    per_page = request.args.get("per_page", type=int) or DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_OPTIONS:
        per_page = DEFAULT_PER_PAGE
    requested_page = request.args.get("page", type=int) or 1

    bonds_all: list[BondDTO] = [
        b
        for b in _service.list_all()
        if b.maturity_date >= today and (bond_type_filter is None or b.bond_type == bond_type_filter)
    ]
    quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in _quote_service.list_all()}

    # Pre-compute yields so the template doesn't need math operations
    yields: dict[int, tuple[float | None, float | None]] = {}
    for bond in bonds_all:
        if bond.id is not None:
            quote: BondQuoteDTO | None = quotes.get(bond.id)
            if quote is not None:
                yields[bond.id] = _calc_bond_yields(bond=bond, last_price=quote.last_price, today=today)

    bonds_sorted = _sort_bonds(bonds_all, yields, sort, direction)
    bonds, page, total_pages = _paginate(bonds_sorted, requested_page, per_page)

    def page_url(p: int) -> str:
        return url_for("bonds.index", bond_type=bond_type_filter, sort=sort, dir=direction, per_page=per_page, page=p)

    sort_urls = {
        field: url_for(
            "bonds.index",
            bond_type=bond_type_filter,
            sort=field,
            dir=_toggle_sort_dir(sort, direction, field),
            per_page=per_page,
        )
        for field in SORT_FIELDS
    }

    return render_template(
        template_name_or_list="bonds/index.html",
        bonds=bonds,
        quotes=quotes,
        yields=yields,
        catalog_filters=CATALOG_FILTERS,
        bond_type_filter=bond_type_filter,
        sort=sort,
        dir=direction,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        per_page_options=PER_PAGE_OPTIONS,
        total_count=len(bonds_all),
        page_url=page_url,
        sort_urls=sort_urls,
    )


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
            "X-Accel-Buffering": "no",  # disable Nginx buffering
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
    gross_yield, net_yield = _calc_bond_yields(bond, quote.last_price, today) if quote else (None, None)
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


@bond_bp.route("/calculator", methods=["GET"])
def calculator():
    """
    Show the BOT calculator page.

    An optional ?bond_id=<id> query parameter pre-selects a specific bond
    (used when navigating here from the bond detail page).
    Without it, the bond with the nearest maturity date is pre-selected.
    """
    today: date = date.today()
    bonds: list[BondDTO] = sorted(
        (b for b in _service.list_all() if b.maturity_date >= today),
        key=lambda b: b.maturity_date,
    )
    quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in _quote_service.list_all()}
    bank_profiles_json = json.dumps(_bank_service.profiles_with_commissions_json())
    preselect_id: int | None = request.args.get("bond_id", type=int)
    bond = _service.get_by_id(preselect_id) if preselect_id is not None else (bonds[0] if bonds else None)
    return render_template(
        "bonds/calculator.html",
        bonds=bonds,
        quotes=quotes,
        bond=bond,
        bank_profiles_json=bank_profiles_json,
        tx=None,
        result=None,
    )


@bond_bp.route("/calculator", methods=["POST"])
def calculator_compute():
    """Receive form data, run the calculator and render the result."""
    today: date = date.today()
    bonds: list[BondDTO] = sorted(
        (b for b in _service.list_all() if b.maturity_date >= today),
        key=lambda b: b.maturity_date,
    )
    quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in _quote_service.list_all()}

    form = request.form
    bank_profiles_json = json.dumps(_bank_service.profiles_with_commissions_json())
    bond_id_raw = form.get("bond_id", "").strip()
    if not bond_id_raw:
        flash("Seleziona un BOT.", "warning")
        return render_template(
            "bonds/calculator.html",
            bonds=bonds,
            quotes=quotes,
            bond=None,
            tx=form,
            result=None,
            bank_profiles_json=bank_profiles_json,
        ), 422

    # ---- Resolve bond (from DB or from manual form fields) ----
    if bond_id_raw == "manual":
        try:
            bond = BondDTO(
                id=None,
                name="BOT Manuale",
                isin="N/D",
                bond_type="BOT",
                issue_date=_parse_date(form["manual_issue_date"]),
                maturity_date=_parse_date(form["manual_maturity_date"]),
                issue_price=float(form["manual_issue_price"]),
                redemption_price=float(form.get("manual_redemption_price") or 100.0),
                tax_rate=12.5,
            )
        except (KeyError, ValueError) as e:
            flash(f"Dati BOT manuale non validi: {e}", "danger")
            return render_template(
                "bonds/calculator.html",
                bonds=bonds,
                quotes=quotes,
                bond=None,
                tx=form,
                result=None,
                bank_profiles_json=bank_profiles_json,
            ), 422
        bond_id = 0  # sentinel for manual BOT
    else:
        bond_id = int(bond_id_raw)
        bond = _service.get_by_id(bond_id)
        if bond is None:
            flash("BOT non trovato.", "warning")
            return render_template(
                "bonds/calculator.html",
                bonds=bonds,
                quotes=quotes,
                bond=None,
                tx=form,
                result=None,
                bank_profiles_json=bank_profiles_json,
            ), 422

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

    def _f(field: str, default: str = "0") -> float:
        raw = (form.get(field, default) or default).strip()
        try:
            return float(raw)
        except ValueError:
            label = _FIELD_LABELS.get(field, field)
            raise ValueError(f"Il campo «{label}» non è un numero valido (valore ricevuto: «{raw}»)")

    try:
        has_sale = form.get("has_sale") == "on"
        sale_date = _parse_date(form["sale_date"]) if has_sale and form.get("sale_date") else None
        buy_max_raw = form.get("buy_commission_max", "").strip()
        sell_max_raw = form.get("sell_commission_max", "").strip()

        sale_price: float | None = None
        if has_sale and form.get("sale_price"):
            sale_price = _f("sale_price")

        tx = BotTransactionDTO(
            bond_id=bond_id,
            purchase_venue=form["purchase_venue"],  # type: ignore[arg-type]
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
            stamp_duty_period=form.get("stamp_duty_period", "quarterly"),
            portfolio_losses=_f("portfolio_losses"),
        )
        result = _calculator_service.calculate(tx, bond)
    except ValidationError as e:
        # Extract the first human-readable Pydantic error message
        first = e.errors()[0]
        msg = first.get("msg", str(e)).removeprefix("Value error, ")
        flash(f"Errore: {msg}", "danger")
        return render_template(
            "bonds/calculator.html",
            bonds=bonds,
            quotes=quotes,
            bond=bond,
            tx=form,
            result=None,
            bank_profiles_json=bank_profiles_json,
        ), 422
    except ValueError as e:
        flash(f"Errore nei parametri: {e}", "danger")
        return render_template(
            "bonds/calculator.html",
            bonds=bonds,
            quotes=quotes,
            bond=bond,
            tx=form,
            result=None,
            bank_profiles_json=bank_profiles_json,
        ), 422

    return render_template(
        "bonds/calculator.html",
        bonds=bonds,
        quotes=quotes,
        bond=bond,
        tx=form,
        result=result,
        bank_profiles_json=bank_profiles_json,
    )
