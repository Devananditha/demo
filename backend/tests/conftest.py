"""Pytest shared test fixtures and configuration for ServiceYield AI."""

import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure app is discoverable on python path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.data.loader import load_fixture_data, load_fixture_raw
from app.fixtures import S_MATH_01_FIXTURE_PATH
from app.models.base import Base
import app.models.canonical  # noqa: F401
from app.schemas.domain import DealershipSnapshotSchema


@pytest.fixture(scope="session")
def raw_fixture_dict() -> dict:
    """Provides raw dictionary of S-MATH-01 fixture."""
    return load_fixture_raw(S_MATH_01_FIXTURE_PATH)


@pytest.fixture(scope="session")
def validated_snapshot() -> DealershipSnapshotSchema:
    """Provides validated Pydantic snapshot schema of S-MATH-01."""
    return load_fixture_data(S_MATH_01_FIXTURE_PATH)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated, in-memory SQLite database session with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
