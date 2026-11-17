"""SQLAlchemy 2.0 Database Engine & Session Factory Configuration."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Default to local SQLite database file, or read DATABASE_URL if configured
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///serviceyield.db")

# For SQLite, enable check_same_thread=False for testing convenience
connect_args = {}
if DEFAULT_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DEFAULT_DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency helper yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
