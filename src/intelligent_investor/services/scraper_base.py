# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Base scraper interface and registry.

Every scraper is a service that subclasses BaseScraper and implements
scrape(), a generator that yields ScraperEvent dicts describing progress.

To add a new scraper:
    1. Create a module in services/ (e.g. my_scraper.py) with a class
       that extends BaseScraper.
    2. Register it at the bottom of that module:
           ScraperRegistry.register("my_key", MyScraperClass)
    3. Export it from services/__init__.py.

Usage
-----
from intelligent_investor.services import ScraperRegistry

for event in ScraperRegistry.run("teleborsa_bot"):
    # event: {"type": "progress"|"done"|"error", "pct": 0-100, "message": "..."}
    print(event)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import TypedDict

# ---------------------------------------------------------------------------
# Event payload
# ---------------------------------------------------------------------------

class ScraperEvent(TypedDict):
    """
    A single status event emitted by a scraper.

    type    : "progress" | "done" | "error"
    pct     : integer 0-100 representing completion
    message : human-readable description of current step
    """
    type: str
    pct: int
    message: str


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseScraper(ABC):
    """
    Abstract base class for all scraper services.

    Subclasses implement scrape(), which must be a generator that:
    - yields ScraperEvent dicts during execution
    - terminates with a final event whose type is "done" or "error"
    """

    @abstractmethod
    def scrape(self) -> Generator[ScraperEvent, None, None]:
        """
        Run the scraping job.

        Yields
        ------
        ScraperEvent dicts.  The last event must have type "done" or "error".
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ScraperRegistry:
    """
    Central catalogue of all registered scraper services.

    Scrapers are keyed by a short identifier string (e.g. "teleborsa_bot").
    Registration happens at module import time inside each scraper module.
    """

    _registry: dict[str, type[BaseScraper]] = {}

    @classmethod
    def register(cls, name: str, scraper_class: type[BaseScraper]) -> None:
        """Register *scraper_class* under the given *name*."""
        cls._registry[name] = scraper_class

    @classmethod
    def get(cls, name: str) -> BaseScraper:
        """
        Instantiate and return the scraper registered under *name*.

        Raises
        ------
        KeyError if *name* is unknown.
        """
        if name not in cls._registry:
            raise KeyError(
                f"Scraper '{name}' not registered. "
                f"Available: {list(cls._registry)}"
            )
        return cls._registry[name]()

    @classmethod
    def run(cls, name: str) -> Generator[ScraperEvent, None, None]:
        """Instantiate the scraper named *name* and return its scrape() generator."""
        return cls.get(name).scrape()

    @classmethod
    def available(cls) -> list[str]:
        """Return the list of all registered scraper names."""
        return list(cls._registry)
