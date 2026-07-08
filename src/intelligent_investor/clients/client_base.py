# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Base client interface and registry.

Clients are network-layer components that fetch and parse data from external
sources (websites, APIs, feeds).  They are called *from within* the application
(by services), in contrast to controllers which are called *from outside*.

Each client subclasses BaseClient and implements fetch(), a generator that:
  - yields ClientEvent dicts to report progress
  - yields one final ClientEvent with type "data" carrying the parsed payload
  - yields one final ClientEvent with type "done" or "error"

To add a new client:
    1. Create a module in clients/ (e.g. my_client.py) with a class that
       extends BaseClient.
    2. Register it at the bottom of that module:
           ClientRegistry.register("my_key", MyClientClass)
    3. Export it from clients/__init__.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Event payload
# ---------------------------------------------------------------------------

class ClientEvent(TypedDict):
    """
    A single status or data event emitted by a client.

    type    : "progress" | "data" | "done" | "error"
    pct     : integer 0-100 representing fetch/parse completion
    message : human-readable description of the current step
    payload : present only on type="data"; the parsed result
    """
    type: str
    pct: int
    message: str
    payload: Any  # only populated when type == "data"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseClient(ABC):
    """
    Abstract base class for all network clients.

    Subclasses implement fetch(), a generator that yields ClientEvent dicts
    during HTTP fetching and parsing and terminates with type "done" or "error".
    Parsed data is delivered via a "data" event before the terminal event.
    """

    @abstractmethod
    def fetch(self) -> Generator[ClientEvent, None, None]:
        """
        Run the fetch+parse job.

        Yields
        ------
        ClientEvent dicts.  The last event must have type "done" or "error".
        A "data" event (if any) must be yielded before the terminal event.
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ClientRegistry:
    """
    Central catalogue of all registered network clients.

    Clients are keyed by a short identifier string (e.g. "teleborsa_bot").
    Registration happens at module import time inside each client module.
    """

    _registry: dict[str, type[BaseClient]] = {}

    @classmethod
    def register(cls, name: str, client_class: type[BaseClient]) -> None:
        """Register *client_class* under the given *name*."""
        cls._registry[name] = client_class

    @classmethod
    def get(cls, name: str) -> BaseClient:
        """
        Instantiate and return the client registered under *name*.

        Raises
        ------
        KeyError if *name* is unknown.
        """
        if name not in cls._registry:
            raise KeyError(
                f"Client '{name}' not registered. "
                f"Available: {list(cls._registry)}"
            )
        return cls._registry[name]()

    @classmethod
    def available(cls) -> list[str]:
        """Return the list of all registered client names."""
        return list(cls._registry)
