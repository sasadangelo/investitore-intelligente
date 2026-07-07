# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
# Import concrete scrapers so they self-register in ScraperRegistry
from . import teleborsa_bot_scraper as _  # noqa: F401
from .bond_quote_service import BondQuoteService
from .bond_service import BondService
from .db_initializer import DatabaseInitializer
from .scraper_base import BaseScraper, ScraperEvent, ScraperRegistry

__all__ = [
    "BondService",
    "BondQuoteService",
    "DatabaseInitializer",
    "BaseScraper",
    "ScraperEvent",
    "ScraperRegistry",
]
