"""Seed script — creates demo tenants, users, cameras, cases, and scans.

Idempotent: checks for existing data before inserting.

Demo credentials (LOCAL DEVELOPMENT ONLY):
  Tenant A — username: alice   password: alice123
  Tenant B — username: bob     password: bob123
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Add backend dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.camera import Camera
from app.models.case import Case
from app.models.scan import Scan
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.db.base import Base


def seed_db(db: Session):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Check idempotency
    if db.query(Tenant).first() is not None:
        print("Seed data already exists. Skipping.")
        return

    # ─── Tenants ──────────────────────────────────────────────
    tenant_a = Tenant(id=1, name="Acme Recovery")
    tenant_b = Tenant(id=2, name="Beta Investigations")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    # ─── Users ────────────────────────────────────────────────
    alice = User(
        id=1,
        tenant_id=1,
        username="alice",
        hashed_password=hash_password("alice123"),
        role="admin",
    )
    bob = User(
        id=2,
        tenant_id=2,
        username="bob",
        hashed_password=hash_password("bob123"),
        role="staff",
    )
    db.add_all([alice, bob])
    db.flush()

    # ─── Cameras ──────────────────────────────────────────────
    cam_1001 = Camera(
        id=1, external_id="cam_1001", tenant_id=1, description="Acme truck #12"
    )
    cam_2050 = Camera(
        id=2, external_id="cam_2050", tenant_id=2, description="Beta mobile unit #3"
    )
    # An inactive camera for testing
    cam_inactive = Camera(
        id=3,
        external_id="cam_9999",
        tenant_id=1,
        description="Decommissioned camera",
        is_active=False,
    )
    db.add_all([cam_1001, cam_2050, cam_inactive])
    db.flush()

    # ─── Case for Tenant A (active, VIN 1FTFW1E51NFA12345) ──
    case_a = Case(
        id=1,
        vin="1FTFW1E51NFA12345",
        status="active",
        tenant_id=1,
        assigned_agent_id=1,
        originating_camera_id=1,
        created_at=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 15, 10, 5, 0, tzinfo=timezone.utc),
    )
    db.add(case_a)
    db.flush()

    # ─── Historical scans for VIN 1FTFW1E51NFA12345 ──────────
    scans = [
        Scan(
            camera_id=1,
            plate="7XYZ123",
            vin="1FTFW1E51NFA12345",
            latitude=33.749,
            longitude=-84.388,
            scanned_at=datetime(2026, 8, 15, 9, 30, 0, tzinfo=timezone.utc),
            image_url="https://example.com/scans/img_001.jpg",
        ),
        Scan(
            camera_id=1,
            plate="7XYZ123",
            vin="1FTFW1E51NFA12345",
            latitude=33.755,
            longitude=-84.391,
            scanned_at=datetime(2026, 8, 20, 14, 15, 0, tzinfo=timezone.utc),
            image_url="https://example.com/scans/img_002.jpg",
        ),
        Scan(
            camera_id=2,  # from Tenant B's camera — cross-tenant sighting
            plate="7XYZ123",
            vin="1FTFW1E51NFA12345",
            latitude=34.052,
            longitude=-118.243,
            scanned_at=datetime(2026, 9, 1, 8, 45, 0, tzinfo=timezone.utc),
            image_url="https://example.com/scans/img_003.jpg",
        ),
    ]
    db.add_all(scans)

    db.commit()
    print("Seed data created successfully.")
    print("Demo users: alice/alice123 (Tenant A), bob/bob123 (Tenant B)")


def seed():
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
