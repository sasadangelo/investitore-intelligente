# conftest.py — executed by pytest before any test file is collected.
# Patches db_manager to use an in-memory SQLite engine for all tests,
# then exposes it as a pytest fixture.
import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

import intelligent_investor.core.database as _db_module
from intelligent_investor.models.base import Base
from intelligent_investor.models.bond import BondDAO  # noqa: F401 — registers table in Base metadata
from intelligent_investor.models.bond_quotes import BondQuoteDAO  # noqa: F401 — registers table in Base metadata

_test_engine: Engine = create_engine("sqlite:///:memory:", echo=False)
_db_module.db_manager.engine = _test_engine
_db_module.db_manager.SessionFactory = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)

Base.metadata.create_all(bind=_test_engine)


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    return _test_engine
