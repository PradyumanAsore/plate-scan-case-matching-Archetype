"""SQLAlchemy engine and session factory with automatic local SQLite fallback."""

from __future__ import annotations

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

db_url = get_settings().database_url
connect_args = {}
engine_kwargs = {}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# Test connection to configured DATABASE_URL.
# If local PostgreSQL authentication fails (e.g., local dev without Docker),
# gracefully fallback to a local SQLite database for zero-config local running.
try:
    engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    logger.warning(
        f"Unable to connect to configured DATABASE_URL ({db_url}): {e}. "
        "Falling back to local SQLite database: sqlite:///./platescan.db"
    )
    db_url = "sqlite:///./platescan.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
