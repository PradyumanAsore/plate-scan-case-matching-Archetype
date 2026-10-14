"""Test fixtures: database, test client, demo data, and auth helpers.

Uses a real PostgreSQL database for true transaction/concurrency testing.
DATABASE_URL must point to a test-safe database.
"""

from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Override DATABASE_URL before importing app modules
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql://platescan:changeme_in_production@localhost:5432/platescan",
    ),
)
os.environ["DATABASE_URL"] = TEST_DB_URL
# Point eligibility at the mock inside our own app
os.environ["ELIGIBILITY_SERVICE_URL"] = "http://testserver/mock/partner-network/eligibility"

from app.core.config import get_settings, Settings
from app.core.security import hash_password, create_access_token
from app.db.base import Base
from app.db.session import SessionLocal
from app.core.dependencies import get_db
from app.main import app

# Attempt to connect to configured DB, or fallback to test SQLite
is_postgres = False
try:
    test_engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
    with test_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    is_postgres = test_engine.dialect.name == "postgresql"
except Exception:
    TEST_DB_URL = "sqlite:///./test_runner.db"
    os.environ["DATABASE_URL"] = TEST_DB_URL
    test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    is_postgres = False

TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session, drop after."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    if is_postgres:
        with test_engine.connect() as conn:
            try:
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_cases_vin_open_unique "
                    "ON cases (vin) WHERE status IN ('pending_claim', 'active')"
                ))
            except Exception:
                pass

            for stmt in [
                "ALTER TABLE cases ADD CONSTRAINT ck_cases_status "
                "CHECK (status IN ('pending_claim', 'active', 'closed'))",
                "ALTER TABLE cases ADD CONSTRAINT ck_cases_pending_no_owner "
                "CHECK ((status != 'pending_claim') OR (tenant_id IS NULL AND assigned_agent_id IS NULL))",
                "ALTER TABLE cases ADD CONSTRAINT ck_cases_active_has_owner "
                "CHECK ((status != 'active') OR (tenant_id IS NOT NULL AND assigned_agent_id IS NOT NULL))",
            ]:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
            conn.commit()

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Clean all tables between tests for isolation."""
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DELETE FROM {table.name}"))
        conn.commit()
    yield


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """FastAPI test client with overridden DB dependency."""

    def override_get_db():
        try:
            yield db
        finally:
            pass  # db closed in the db fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Seed helpers ────────────────────────────────────────────────────────────

from app.models.tenant import Tenant
from app.models.user import User
from app.models.camera import Camera
from app.models.case import Case
from app.models.scan import Scan


@pytest.fixture
def tenants(db):
    t1 = Tenant(id=1, name="Acme Recovery")
    t2 = Tenant(id=2, name="Beta Investigations")
    db.add_all([t1, t2])
    db.commit()
    return t1, t2


@pytest.fixture
def users(db, tenants):
    alice = User(
        id=1, tenant_id=1, username="alice",
        hashed_password=hash_password("alice123"), role="admin",
    )
    bob = User(
        id=2, tenant_id=2, username="bob",
        hashed_password=hash_password("bob123"), role="staff",
    )
    db.add_all([alice, bob])
    db.commit()
    return alice, bob


@pytest.fixture
def cameras(db, tenants):
    cam1 = Camera(id=1, external_id="cam_1001", tenant_id=1, description="Acme truck #12")
    cam2 = Camera(id=2, external_id="cam_2050", tenant_id=2, description="Beta mobile #3")
    cam_inactive = Camera(
        id=3, external_id="cam_9999", tenant_id=1,
        description="Decommissioned", is_active=False,
    )
    db.add_all([cam1, cam2, cam_inactive])
    db.commit()
    return cam1, cam2, cam_inactive


@pytest.fixture
def active_case_a(db, users, cameras):
    """Create Tenant A's active case for VIN 1FTFW1E51NFA12345."""
    case = Case(
        id=1, vin="1FTFW1E51NFA12345", status="active",
        tenant_id=1, assigned_agent_id=1, originating_camera_id=1,
    )
    db.add(case)
    db.commit()
    return case


@pytest.fixture
def sample_scans(db, cameras, active_case_a):
    """Historical scans for VIN 1FTFW1E51NFA12345 from multiple cameras."""
    scans = [
        Scan(
            camera_id=1, plate="7XYZ123", vin="1FTFW1E51NFA12345",
            latitude=33.749, longitude=-84.388,
            scanned_at=datetime(2026, 8, 15, 9, 30, tzinfo=timezone.utc),
            image_url="https://example.com/img_001.jpg",
        ),
        Scan(
            camera_id=2, plate="7XYZ123", vin="1FTFW1E51NFA12345",
            latitude=34.052, longitude=-118.243,
            scanned_at=datetime(2026, 9, 1, 8, 45, tzinfo=timezone.utc),
            image_url="https://example.com/img_002.jpg",
        ),
    ]
    db.add_all(scans)
    db.commit()
    return scans


def auth_header(user_id: int) -> dict[str, str]:
    """Create an Authorization header with a valid JWT for the given user ID."""
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def alice_headers():
    return auth_header(1)


@pytest.fixture
def bob_headers():
    return auth_header(2)
