# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from flask import Blueprint, flash, redirect, render_template, request, url_for
from pydantic import ValidationError

from intelligent_investor.dtos.bank_profile import BankCommissionDTO, BankProfileDTO
from intelligent_investor.services.bank_profile_service import BankProfileService

bank_bp = Blueprint("banks", __name__, url_prefix="/banks")
_service = BankProfileService()

VENUE_LABELS = {"asta": "Asta", "mot": "MOT"}
DURATION_LABELS = {"any": "Qualsiasi", "annual": "Annuale", "semiannual": "Semestrale", "quarterly": "Trimestrale"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _form_to_profile(form: dict, profile_id: int | None = None) -> BankProfileDTO:
    return BankProfileDTO(
        id=profile_id,
        bank_name=form["bank_name"].strip(),
        profile_name=form["profile_name"].strip(),
        notes=form.get("notes", "").strip() or None,
        info_url=form.get("info_url", "").strip() or None,
    )


def _form_to_commission(form: dict, profile_id: int, commission_id: int | None = None) -> BankCommissionDTO:
    max_raw = form.get("commission_max", "").strip()
    min_raw = form.get("days_min", "").strip()
    max_days_raw = form.get("days_max", "").strip()
    return BankCommissionDTO(
        id=commission_id,
        profile_id=profile_id,
        venue=form["venue"],
        duration_type=form.get("duration_type", "any"),
        days_min=int(min_raw) if min_raw else None,
        days_max=int(max_days_raw) if max_days_raw else None,
        commission_pct=float(form.get("commission_pct", 0)),
        commission_min=float(form.get("commission_min", 0)),
        commission_max=float(max_raw) if max_raw else None,
        commission_fixed=float(form.get("commission_fixed", 0)),
    )


# ---------------------------------------------------------------------------
# Profile routes
# ---------------------------------------------------------------------------

@bank_bp.route("/", methods=["GET"])
def index():
    """List all bank profiles with their commission counts."""
    profiles = _service.list_profiles()
    commission_counts = {p.id: len(_service.list_commissions(p.id)) for p in profiles}
    return render_template("banks/index.html",
                           profiles=profiles,
                           commission_counts=commission_counts)


@bank_bp.route("/new", methods=["GET"])
def new_profile():
    return render_template("banks/form_profile.html",
                           profile=None,
                           action=url_for("banks.create_profile"),
                           title="Nuovo Profilo Banca")


@bank_bp.route("/", methods=["POST"])
def create_profile():
    try:
        dto = _form_to_profile(request.form)
        created = _service.create_profile(dto)
        flash("Profilo creato con successo.", "success")
        return redirect(url_for("banks.detail", profile_id=created.id))
    except (ValueError, ValidationError) as e:
        flash(f"Errore: {e}", "danger")
        return render_template("banks/form_profile.html",
                               profile=request.form,
                               action=url_for("banks.create_profile"),
                               title="Nuovo Profilo Banca"), 422


@bank_bp.route("/<int:profile_id>", methods=["GET"])
def detail(profile_id: int):
    """Show a profile with all its commission rows."""
    profile = _service.get_profile(profile_id)
    if profile is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    commissions = _service.list_commissions(profile_id)
    return render_template("banks/detail.html",
                           profile=profile,
                           commissions=commissions,
                           venue_labels=VENUE_LABELS,
                           duration_labels=DURATION_LABELS)


@bank_bp.route("/<int:profile_id>/edit", methods=["GET"])
def edit_profile(profile_id: int):
    profile = _service.get_profile(profile_id)
    if profile is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    return render_template("banks/form_profile.html",
                           profile=profile,
                           action=url_for("banks.update_profile", profile_id=profile_id),
                           title="Modifica Profilo Banca")


@bank_bp.route("/<int:profile_id>", methods=["POST"])
def update_profile(profile_id: int):
    if _service.get_profile(profile_id) is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    try:
        dto = _form_to_profile(request.form, profile_id=profile_id)
        _service.update_profile(dto)
        flash("Profilo aggiornato.", "success")
        return redirect(url_for("banks.detail", profile_id=profile_id))
    except (ValueError, ValidationError) as e:
        flash(f"Errore: {e}", "danger")
        return render_template("banks/form_profile.html",
                               profile=request.form,
                               action=url_for("banks.update_profile", profile_id=profile_id),
                               title="Modifica Profilo Banca"), 422


@bank_bp.route("/<int:profile_id>/delete", methods=["GET"])
def confirm_delete_profile(profile_id: int):
    profile = _service.get_profile(profile_id)
    if profile is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    return render_template("banks/confirm_delete_profile.html", profile=profile)


@bank_bp.route("/<int:profile_id>/delete", methods=["POST"])
def delete_profile(profile_id: int):
    _service.delete_profile(profile_id)
    flash("Profilo eliminato.", "success")
    return redirect(url_for("banks.index"))


# ---------------------------------------------------------------------------
# Commission routes
# ---------------------------------------------------------------------------

@bank_bp.route("/<int:profile_id>/commissions/new", methods=["GET"])
def new_commission(profile_id: int):
    profile = _service.get_profile(profile_id)
    if profile is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    return render_template("banks/form_commission.html",
                           profile=profile,
                           commission=None,
                           venue_labels=VENUE_LABELS,
                           duration_labels=DURATION_LABELS,
                           action=url_for("banks.create_commission", profile_id=profile_id),
                           title="Nuova Commissione")


@bank_bp.route("/<int:profile_id>/commissions", methods=["POST"])
def create_commission(profile_id: int):
    if _service.get_profile(profile_id) is None:
        flash("Profilo non trovato.", "warning")
        return redirect(url_for("banks.index"))
    try:
        dto = _form_to_commission(request.form, profile_id=profile_id)
        _service.create_commission(dto)
        flash("Commissione aggiunta.", "success")
        return redirect(url_for("banks.detail", profile_id=profile_id))
    except (ValueError, ValidationError) as e:
        flash(f"Errore: {e}", "danger")
        profile = _service.get_profile(profile_id)
        return render_template("banks/form_commission.html",
                               profile=profile,
                               commission=request.form,
                               venue_labels=VENUE_LABELS,
                               duration_labels=DURATION_LABELS,
                               action=url_for("banks.create_commission", profile_id=profile_id),
                               title="Nuova Commissione"), 422


@bank_bp.route("/<int:profile_id>/commissions/<int:commission_id>/edit", methods=["GET"])
def edit_commission(profile_id: int, commission_id: int):
    profile = _service.get_profile(profile_id)
    commission = _service.get_commission(commission_id)
    if profile is None or commission is None:
        flash("Elemento non trovato.", "warning")
        return redirect(url_for("banks.index"))
    return render_template("banks/form_commission.html",
                           profile=profile,
                           commission=commission,
                           venue_labels=VENUE_LABELS,
                           duration_labels=DURATION_LABELS,
                           action=url_for("banks.update_commission",
                                         profile_id=profile_id, commission_id=commission_id),
                           title="Modifica Commissione")


@bank_bp.route("/<int:profile_id>/commissions/<int:commission_id>", methods=["POST"])
def update_commission(profile_id: int, commission_id: int):
    try:
        dto = _form_to_commission(request.form, profile_id=profile_id, commission_id=commission_id)
        _service.update_commission(dto)
        flash("Commissione aggiornata.", "success")
        return redirect(url_for("banks.detail", profile_id=profile_id))
    except (ValueError, ValidationError) as e:
        flash(f"Errore: {e}", "danger")
        profile = _service.get_profile(profile_id)
        return render_template("banks/form_commission.html",
                               profile=profile,
                               commission=request.form,
                               venue_labels=VENUE_LABELS,
                               duration_labels=DURATION_LABELS,
                               action=url_for("banks.update_commission",
                                             profile_id=profile_id, commission_id=commission_id),
                               title="Modifica Commissione"), 422


@bank_bp.route("/<int:profile_id>/commissions/<int:commission_id>/delete", methods=["POST"])
def delete_commission(profile_id: int, commission_id: int):
    _service.delete_commission(commission_id)
    flash("Commissione eliminata.", "success")
    return redirect(url_for("banks.detail", profile_id=profile_id))
