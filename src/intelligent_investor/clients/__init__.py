# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
# Import concrete clients so they self-register in ClientRegistry
from . import teleborsa_bot_client as _  # noqa: F401
from .client_base import BaseClient, ClientEvent, ClientRegistry

__all__ = ["BaseClient", "ClientEvent", "ClientRegistry"]
