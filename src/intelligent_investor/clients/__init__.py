# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
# Import concrete clients so they self-register in ClientRegistry
from . import teleborsa_bot_client as _bot_client  # noqa: F401
from . import teleborsa_btp_client as _btp_client  # noqa: F401
from .client_base import BaseClient, ClientEvent, ClientRegistry

__all__ = ["BaseClient", "ClientEvent", "ClientRegistry"]
