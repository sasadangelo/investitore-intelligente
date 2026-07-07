# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from sqlalchemy.orm import declarative_base

# Base class shared by all ORM models (DAOs).
# Must be imported here — do NOT import it from any other module.
Base = declarative_base()
