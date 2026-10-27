# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from sqlalchemy import inspect, text

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.db.base import Base
from intelligent_investor.db.session import db_manager

# Import all DAOs here so SQLAlchemy's metadata is aware of every table
from intelligent_investor.models.bond import BondDAO  # noqa: F401
from intelligent_investor.models.bond_quotes import BondQuoteDAO  # noqa: F401

logger = LoggerManager.get_logger(name="DatabaseInitializer")

# Columns added to existing tables after their creation: create_all does not alter
# tables that already exist, so they are added by _migrate. Only nullable columns.
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column, SQL type)
    ("bond", "first_coupon_date", "DATE"),  # BTP roadmap phase 10
]


class DatabaseInitializer:
    """Creates (or verifies) all database tables at application startup."""

    def __init__(self) -> None:
        self._engine = db_manager.engine

    def initialize_tables(self) -> None:
        """Create tables in the SQLite database if they do not already exist."""
        logger.info("Verifying and initialising database schema...")
        try:
            Base.metadata.create_all(bind=self._engine)
            self._migrate()
            logger.info("Database schema initialised successfully.")
        except Exception as e:
            logger.error(f"Critical error during table creation: {e}")
            raise

    def _migrate(self) -> None:
        """Add to existing tables the columns of _ADDED_COLUMNS they do not have yet."""
        inspector = inspect(self._engine)
        with self._engine.begin() as conn:
            for table, column, sql_type in _ADDED_COLUMNS:
                existing = {c["name"] for c in inspector.get_columns(table)}
                if column not in existing:
                    logger.info(f"Adding column {table}.{column}")
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
