# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Entry point for the Investitore Intelligente Flask application.

Usage:
    uv run python app.py
    # oppure
    flask --app app run
"""

import os
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from flask.app import Flask
from werkzeug.wrappers.response import Response

# Make the 'src' package importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent / "src"))

# ---------------------------------------------------------------------------
# Import config first. config.py loads and validates config.yaml at import
# time: if the file is missing or contains invalid values the import raises
# and the process stops here with a clear message.
# ---------------------------------------------------------------------------
try:
    from intelligent_investor.core.config import config
except FileNotFoundError as exc:
    print(f"[ERRORE CONFIGURAZIONE] {exc}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f"[ERRORE CONFIGURAZIONE] Valore non valido in config.yaml:\n{exc}", file=sys.stderr)
    sys.exit(1)

from flask import Flask, redirect, url_for

from intelligent_investor.controllers import bank_bp, bond_bp, bot_auction_bp, guide_bp
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.services import DatabaseInitializer

logger = LoggerManager.get_logger("App")


def create_app() -> Flask:
    """Application factory."""
    app: Flask = Flask(
        import_name=__name__,
        template_folder="src/intelligent_investor/templates",
        static_folder="src/intelligent_investor/static",
    )

    # Secret key — required for flash messages / sessions
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Initialise database tables
    DatabaseInitializer().initialize_tables()

    # Register Blueprints
    app.register_blueprint(blueprint=bond_bp)
    app.register_blueprint(blueprint=bot_auction_bp)
    app.register_blueprint(blueprint=bank_bp)
    app.register_blueprint(blueprint=guide_bp)

    # Custom Jinja2 filter: round to 2 decimals with ROUND_HALF_UP, returns formatted string
    @app.template_filter("r2")
    def round2_filter(value: float) -> str:
        try:
            rounded = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return f"{rounded:.2f}"
        except Exception:
            return str(value)

    # Root redirect → bonds list
    @app.route(rule="/")
    def index() -> Response:
        return redirect(location=url_for(endpoint="bonds.index"))

    logger.info("Flask application created and configured.")
    return app


if __name__ == "__main__":
    application: Flask = create_app()
    application.run(
        host=config.app.host,
        port=config.app.port,
        debug=config.app.debug,
    )
