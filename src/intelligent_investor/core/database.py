# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from intelligent_investor.core.config import config
from intelligent_investor.core.log import LoggerManager

logger = LoggerManager.get_logger(name="DatabaseSession")


class DatabaseSessionManager:
    def __init__(self) -> None:
        # Retrieve the typed SQLiteSettings object from Pydantic config
        sqlite_settings = config.database.sqlite

        # Ensure the destination directory (e.g. 'data/') exists
        db_file_path: Path = sqlite_settings.absolute_path
        db_file_path.parent.mkdir(parents=True, exist_ok=True)

        self.database_url = sqlite_settings.database_url

        # Configure the SQLite-specific engine
        # 'check_same_thread=False' is required to allow the DB to be used
        # safely across threads via SQLAlchemy's isolated session contexts
        self.engine = create_engine(
            url=self.database_url,
            echo=sqlite_settings.echo,
            pool_pre_ping=sqlite_settings.pool_pre_ping,
            connect_args={"check_same_thread": False} if self.database_url.startswith("sqlite") else {},
        )

        # Force SQLite to honour Foreign Key constraints (ON DELETE CASCADE, etc.)
        @event.listens_for(target=self.engine, identifier="connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        logger.info(f"SQLite engine initialised for file: {db_file_path}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for transactional session management with performance logging."""
        session: Session = self.SessionFactory()
        start_time: float = time.perf_counter()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("SQLAlchemyError in database session — rollback executed")
            raise e
        except Exception as e:
            session.rollback()
            logger.exception("Unexpected error in database session — rollback executed")
            raise e
        finally:
            elapsed: float = time.perf_counter() - start_time
            logger.info(f"Database operation completed in {elapsed:.4f}s")
            session.close()


# Global manager instance to be imported by services
db_manager: DatabaseSessionManager = DatabaseSessionManager()
