# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Controller for the "Catalogo" menu entry.

Reads and validates the catalogue query parameters (filter, sorting, pagination and
the optional purchase costs of the "Parametri avanzati" panel), fetches the entries
from CatalogueService and renders them. Also streams the
quote refresh progress to the browser. Bond creation/editing lives in bond_controller.
"""
import json
from collections.abc import Generator

from flask import Blueprint, Response, flash, render_template, request, stream_with_context, url_for
from werkzeug.datastructures import MultiDict

from intelligent_investor.services import BondSyncService
from intelligent_investor.services.bank_profile_service import BankProfileService
from intelligent_investor.services.catalogue_service import SORT_FIELDS, CatalogueService, PurchaseCosts
from intelligent_investor.utils.pagination import paginate

catalogue_bp = Blueprint("catalogue", __name__, url_prefix="/catalogue")

# Module-level singletons: services are stateless, so one instance serves every request
_catalogue_service = CatalogueService()
_sync_service = BondSyncService()
_bank_service = BankProfileService()

# Accepted values for the ?bond_type= filter, as (value, label) — restricted to the types in use for now.
# The label is what the dropdown shows; any other value is ignored and the catalogue shows all types.
CATALOG_FILTERS: list[tuple[str, str]] = [("BOT", "BOT"), ("BTP", "BTP Tasso Fisso")]

# Direction applied when the user first clicks a column header (or sends ?sort= without ?dir=):
# earliest maturity first, highest yield first
SORT_DEFAULT_DIR: dict[str, str] = {"maturity": "asc", "yield_gross": "desc", "yield_net": "desc"}

# Accepted values for the ?per_page= parameter, and the fallback for missing/invalid values
PER_PAGE_OPTIONS: tuple[int, ...] = (10, 20, 50, 100)
DEFAULT_PER_PAGE = 20

# Query parameters of the "Parametri avanzati" panel. They are carried over by every catalogue
# link (sorting, pagination, filter) so the costs stay applied while browsing.
COST_PARAMS: tuple[str, ...] = (
    "face_value",
    "bank_profile_id",
    "commission_pct",
    "commission_min",
    "commission_max",
    "commission_fixed",
    "portfolio_losses",
)

# Quote sources refreshed by "Aggiorna Quotazioni", in order: (sync source, log label)
_SYNC_SOURCES: tuple[tuple[str, str], ...] = (("teleborsa_bot", "BOT"), ("teleborsa_btp", "BTP"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _toggle_sort_dir(current_sort: str, current_dir: str, field: str) -> str:
    """
    Return the direction that clicking the *field* column header should switch to.

    Clicking the column the table is already sorted by flips the direction; clicking
    another column starts from that column's default direction.

    Args:
        current_sort: Field the table is currently sorted by
        current_dir: Current direction, "asc" or "desc"
        field: Field of the column header being rendered

    Returns:
        "asc" or "desc"
    """
    if current_sort == field:
        return "desc" if current_dir == "asc" else "asc"
    return SORT_DEFAULT_DIR[field]


def _read_costs(args: MultiDict[str, str]) -> tuple[PurchaseCosts | None, dict[str, str]]:
    """
    Read the purchase costs of the "Parametri avanzati" panel from the query string.

    The costs are active only when a lot (face_value) is given. Blank fields count as 0,
    except commission_max, where blank means "no cap", and bank_profile_id, where blank
    means "commissions entered by hand".

    Args:
        args: The request query parameters

    Returns:
        (costs, params): costs is None when the panel is not used; params holds the
        non-blank COST_PARAMS as received, to carry over in the catalogue links

    Raises:
        ValueError: if a value is not a number, or the lot is not a positive multiple of 100
    """
    params = {name: args[name].strip() for name in COST_PARAMS if args.get(name, "").strip()}
    if "face_value" not in params:
        return None, params

    def number(name: str) -> float:
        """Parse *name* as a non-negative float (blank -> 0)."""
        value = float(params.get(name, "0").replace(",", "."))
        if value < 0:
            raise ValueError(f"{name} must not be negative")
        return value

    face_value = number("face_value")
    if face_value <= 0 or face_value % 100 != 0:
        raise ValueError("face_value must be a positive multiple of 100")
    costs = PurchaseCosts(
        face_value=face_value,
        bank_profile_id=int(params["bank_profile_id"]) if "bank_profile_id" in params else None,
        commission_pct=number("commission_pct"),
        commission_min=number("commission_min"),
        commission_max=number("commission_max") if "commission_max" in params else None,
        commission_fixed=number("commission_fixed"),
        portfolio_losses=number("portfolio_losses"),
    )
    return costs, params


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@catalogue_bp.route(rule="/", methods=["GET"])
def index() -> str:
    """
    GET /catalogue/ — list the bonds not yet matured, with quotes and yields.

    Query parameters (invalid values fall back to the default):
        bond_type: optional filter, one of CATALOG_FILTERS
        sort, dir: one of SORT_FIELDS and "asc"|"desc" (default: maturity ascending)
        page, per_page: pagination, per_page restricted to PER_PAGE_OPTIONS
        COST_PARAMS: optional lot, commissions and zainetto of a real purchase; invalid
            values are ignored with a warning

    Returns:
        The rendered catalogue page
    """
    # ---- Read and validate the query parameters (invalid values -> defaults) ----
    bond_type = request.args.get("bond_type") or None
    if bond_type not in {value for value, _ in CATALOG_FILTERS}:
        bond_type = None
    sort = request.args.get("sort", "maturity")
    if sort not in SORT_FIELDS:
        sort = "maturity"
    # The default direction depends on the sort field, so it is resolved after it
    direction = request.args.get("dir") or SORT_DEFAULT_DIR[sort]
    if direction not in ("asc", "desc"):
        direction = SORT_DEFAULT_DIR[sort]
    per_page = request.args.get("per_page", type=int) or DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_OPTIONS:
        per_page = DEFAULT_PER_PAGE

    try:
        costs, cost_params = _read_costs(request.args)
    except ValueError:
        flash("Parametri avanzati non validi: il lotto deve essere un multiplo di 100 e gli importi numeri "
              "non negativi. Rendimenti mostrati senza costi.", "warning")
        costs, cost_params = None, {}

    # ---- Fetch the filtered/sorted entries and cut out the requested page ----
    # An out-of-range ?page= is clamped by paginate(), not rejected
    entries = _catalogue_service.list_entries(bond_type=bond_type, sort=sort, direction=direction, costs=costs)
    page = paginate(entries, page=request.args.get("page", type=int) or 1, per_page=per_page)

    # ---- Build the URLs the template needs, preserving the current filter/sort/page size ----
    def page_url(number: int) -> str:
        """URL of page *number* with the current filter, sorting and page size (used by the pager)."""
        return url_for(
            "catalogue.index",
            bond_type=bond_type,
            sort=sort,
            dir=direction,
            per_page=per_page,
            page=number,
            **cost_params,
        )

    # One URL per sortable column header; changing the sort always goes back to page 1
    sort_urls = {
        field: url_for(
            "catalogue.index",
            bond_type=bond_type,
            sort=field,
            dir=_toggle_sort_dir(sort, direction, field),
            per_page=per_page,
            **cost_params,
        )
        for field in SORT_FIELDS
    }

    return render_template(
        template_name_or_list="catalogue/index.html",
        page=page,
        catalog_filters=CATALOG_FILTERS,
        bond_type_filter=bond_type,
        sort=sort,
        dir=direction,
        per_page_options=PER_PAGE_OPTIONS,
        page_url=page_url,
        sort_urls=sort_urls,
        costs=costs,
        cost_params=cost_params,
        bank_profiles=_bank_service.list_profiles(),
        # Link that keeps filter/sort/page size but drops the costs ("Rimuovi")
        reset_costs_url=url_for("catalogue.index", bond_type=bond_type, sort=sort, dir=direction, per_page=per_page),
    )


@catalogue_bp.route(rule="/refresh-quotes/stream", methods=["GET"])
def refresh_quotes_stream() -> Response:
    """
    GET /catalogue/refresh-quotes/stream — SSE endpoint streaming quote sync progress.

    Runs every source in _SYNC_SOURCES sequentially, scaling each source's 0-100
    progress into its own slice of the overall 0-100 range so the single
    "Aggiorna Quotazioni" button reports one continuous progress bar.

    Each event is a JSON-encoded SyncEvent:
        data: {"type": "progress"|"done"|"error", "pct": 0-100, "message": "..."}

    The stream ends after the final "done" event or at the first "error" event.

    Returns:
        A streaming text/event-stream response
    """

    def _event_stream() -> Generator[str, None, None]:
        """Run the sync sources one after the other and yield their events as SSE messages."""
        # With N sources, source i owns the [i * slice_size, (i + 1) * slice_size] slice of the bar
        slice_size = 100 // len(_SYNC_SOURCES)
        last_idx = len(_SYNC_SOURCES) - 1
        try:
            for idx, (source, label) in enumerate(_SYNC_SOURCES):
                is_last_source = idx == last_idx
                slice_start = idx * slice_size
                for event in _sync_service.sync(source=source):
                    # Rescale the source's own 0-100 progress into its slice of the overall bar
                    event_type = event["type"]
                    if event_type == "done":
                        # Only the final source's "done" event ends the stream; earlier
                        # ones are relabelled "progress" so the browser keeps listening.
                        pct = 100 if is_last_source else slice_start + slice_size
                        if not is_last_source:
                            event_type = "progress"
                    else:
                        pct = slice_start + int(event["pct"] * slice_size / 100)
                    # Prefix the message with the source label so the user knows which sync is running
                    scaled_event = {"type": event_type, "pct": pct, "message": f"[{label}] {event['message']}"}
                    # SSE wire format: one "data:" line per message, terminated by a blank line
                    yield f"data: {json.dumps(obj=scaled_event)}\n\n"
                    # A failed source stops the whole refresh: the remaining sources are not run
                    if event["type"] == "error":
                        return
        except Exception as exc:
            # Unexpected failure: report it as an SSE error so the browser closes the progress bar
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
