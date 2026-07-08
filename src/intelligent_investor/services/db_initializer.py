# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from intelligent_investor.db.session import db_manager
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.db.base import Base

# Import all DAOs here so SQLAlchemy's metadata is aware of every table
from intelligent_investor.models.bond import BondDAO  # noqa: F401
from intelligent_investor.models.bond_quotes import BondQuoteDAO  # noqa: F401

logger = LoggerManager.get_logger("DatabaseInitializer")


class DatabaseInitializer:
    """Creates (or verifies) all database tables at application startup."""

    def __init__(self) -> None:
        self._engine = db_manager.engine

    def initialize_tables(self) -> None:
        """Create tables in the SQLite database if they do not already exist."""
        logger.info("Verifying and initialising database schema...")
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database schema initialised successfully.")
        except Exception as e:
            logger.error(f"Critical error during table creation: {e}")
            raise
