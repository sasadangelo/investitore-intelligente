# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from flask import Blueprint, abort, render_template

from intelligent_investor.services.guide_service import GuideService

guide_bp = Blueprint("guides", __name__, url_prefix="/guides")
_service = GuideService()


@guide_bp.route("/", methods=["GET"])
def index():
    """List all available guides."""
    guides = _service.list_all()
    return render_template("guides/index.html", guides=guides)


@guide_bp.route("/<slug>", methods=["GET"])
def detail(slug: str):
    """Render a single guide by slug."""
    guide = _service.get(slug)
    if guide is None:
        abort(404)
    all_guides = _service.list_all()
    return render_template("guides/detail.html", guide=guide, guides_list=all_guides)
