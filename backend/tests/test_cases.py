"""Tests for Case Claiming, Case Listing, Scan History, and Access Control."""

import pytest
from datetime import datetime, timezone
from app.models.case import Case
from app.models.scan import Scan


class TestCaseClaiming:
    """Case claiming: atomic claiming, cross-tenant claiming, concurrency, state checks."""

    def test_successful_claim_by_originating_tenant(self, client, users, cameras, db, alice_headers):
        """Alice (Tenant A) claims a pending case originated by Tenant A's camera."""
        # Create a pending case
        case = Case(
            vin="1FTFW1E51NFA00001",
            status="pending_claim",
            originating_camera_id=1,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        resp = client.post(f"/api/v1/cases/{case.id}/claim", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == case.id
        assert data["status"] == "active"
        assert data["tenant_id"] == 1
        assert data["assigned_agent_id"] == 1

        # Check DB state
        db.refresh(case)
        assert case.status == "active"
        assert case.tenant_id == 1
        assert case.assigned_agent_id == 1

    def test_successful_cross_tenant_claim(self, client, users, cameras, db, alice_headers):
        """Alice (Tenant A) successfully claims a pending case originated by Bob's (Tenant B) camera."""
        case = Case(
            vin="5NPE34AF9KH999999",
            status="pending_claim",
            originating_camera_id=2,  # cam_2050 (Tenant B)
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        # Alice claims it
        resp = client.post(f"/api/v1/cases/{case.id}/claim", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert data["tenant_id"] == 1
        assert data["assigned_agent_id"] == 1

    def test_claim_already_claimed_returns_409(self, client, users, cameras, db, alice_headers, bob_headers):
        """Claiming a case that is already active returns a 409 conflict."""
        case = Case(
            vin="1FTFW1E51NFA00002",
            status="pending_claim",
            originating_camera_id=1,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        # Alice claims first
        r1 = client.post(f"/api/v1/cases/{case.id}/claim", headers=alice_headers)
        assert r1.status_code == 200

        # Bob attempts to claim the same case
        r2 = client.post(f"/api/v1/cases/{case.id}/claim", headers=bob_headers)
        assert r2.status_code == 409
        assert "already claimed" in r2.json()["detail"].lower()

    def test_claim_closed_case_returns_409(self, client, users, cameras, db, alice_headers):
        """Attempting to claim a closed case returns 409."""
        case = Case(
            vin="1FTFW1E51NFA00003",
            status="closed",
            tenant_id=1,
            assigned_agent_id=1,
            originating_camera_id=1,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        resp = client.post(f"/api/v1/cases/{case.id}/claim", headers=alice_headers)
        assert resp.status_code == 409
        assert "closed" in resp.json()["detail"].lower()

    def test_claim_nonexistent_case_returns_404(self, client, users, alice_headers):
        """Attempting to claim a case that does not exist returns 404."""
        resp = client.post("/api/v1/cases/99999/claim", headers=alice_headers)
        assert resp.status_code == 404


class TestCaseListing:
    """Case listing: visibility rules, tenant isolation, status filtering, pagination."""

    def test_list_cases_shows_own_and_pending_only(self, client, users, cameras, db, alice_headers, bob_headers):
        """Alice can see her own cases + global pending cases, but NEVER Bob's active/closed cases."""
        # 1. Tenant A active case
        case_a_active = Case(vin="VIN_A_ACTIVE", status="active", tenant_id=1, assigned_agent_id=1)
        # 2. Tenant A closed case
        case_a_closed = Case(vin="VIN_A_CLOSED", status="closed", tenant_id=1, assigned_agent_id=1)
        # 3. Tenant B active case (MUST NOT BE VISIBLE TO ALICE)
        case_b_active = Case(vin="VIN_B_ACTIVE", status="active", tenant_id=2, assigned_agent_id=2)
        # 4. Tenant B closed case (MUST NOT BE VISIBLE TO ALICE)
        case_b_closed = Case(vin="VIN_B_CLOSED", status="closed", tenant_id=2, assigned_agent_id=2)
        # 5. Global pending case originated by Tenant B camera (MUST BE VISIBLE TO BOTH)
        case_pending = Case(vin="VIN_PENDING", status="pending_claim", originating_camera_id=2)

        db.add_all([case_a_active, case_a_closed, case_b_active, case_b_closed, case_pending])
        db.commit()

        # Alice's view
        resp_a = client.get("/api/v1/cases", headers=alice_headers)
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        vins_a = [c["vin"] for c in data_a["items"]]

        assert "VIN_A_ACTIVE" in vins_a
        assert "VIN_A_CLOSED" in vins_a
        assert "VIN_PENDING" in vins_a
        assert "VIN_B_ACTIVE" not in vins_a
        assert "VIN_B_CLOSED" not in vins_a

        # Bob's view
        resp_b = client.get("/api/v1/cases", headers=bob_headers)
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        vins_b = [c["vin"] for c in data_b["items"]]

        assert "VIN_B_ACTIVE" in vins_b
        assert "VIN_B_CLOSED" in vins_b
        assert "VIN_PENDING" in vins_b
        assert "VIN_A_ACTIVE" not in vins_b
        assert "VIN_A_CLOSED" not in vins_b

    def test_status_filter_preserves_tenant_isolation(self, client, users, cameras, db, alice_headers):
        """Applying ?status=active only shows own active cases, never foreign active cases."""
        case_a_active = Case(vin="VIN_A_ACT", status="active", tenant_id=1, assigned_agent_id=1)
        case_b_active = Case(vin="VIN_B_ACT", status="active", tenant_id=2, assigned_agent_id=2)
        case_pending = Case(vin="VIN_PEND", status="pending_claim")

        db.add_all([case_a_active, case_b_active, case_pending])
        db.commit()

        resp = client.get("/api/v1/cases?status=active", headers=alice_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["vin"] == "VIN_A_ACT"

    def test_status_filter_pending_claim(self, client, users, cameras, db, alice_headers):
        """Filtering by pending_claim returns pending cases."""
        case_a = Case(vin="VIN_A_ACT", status="active", tenant_id=1, assigned_agent_id=1)
        case_p = Case(vin="VIN_P_001", status="pending_claim")
        db.add_all([case_a, case_p])
        db.commit()

        resp = client.get("/api/v1/cases?status=pending_claim", headers=alice_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["vin"] == "VIN_P_001"

    def test_pagination(self, client, users, cameras, db, alice_headers):
        """Pagination limit & offset work accurately."""
        for i in range(15):
            db.add(Case(vin=f"PAGE_VIN_{i:02d}", status="pending_claim"))
        db.commit()

        resp = client.get("/api/v1/cases?limit=5&offset=0", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 15
        assert len(data["items"]) == 5
        assert data["limit"] == 5
        assert data["offset"] == 0

        # Offset 10
        resp2 = client.get("/api/v1/cases?limit=10&offset=10", headers=alice_headers)
        assert len(resp2.json()["items"]) == 5


class TestScanHistoryAndAccessControl:
    """Historical scan retrieval and tenant boundary enforcement."""

    def test_scan_history_chronological_with_multiple_cameras(
        self, client, users, cameras, active_case_a, sample_scans, alice_headers
    ):
        """Alice can retrieve complete scan history for her case, ordered chronologically."""
        resp = client.get(f"/api/v1/cases/{active_case_a.id}/scans", headers=alice_headers)
        assert resp.status_code == 200
        scans = resp.json()
        assert len(scans) == 2

        # Verify chronological order
        t1 = scans[0]["scanned_at"]
        t2 = scans[1]["scanned_at"]
        assert t1 <= t2

        # Verify sightings came from different cameras/tenants
        cam_ids = [s["camera_id"] for s in scans]
        assert "cam_1001" in cam_ids
        assert "cam_2050" in cam_ids

    def test_pending_case_scan_history_accessible(self, client, users, cameras, db, alice_headers):
        """Authenticated users can view scan history for a pending case."""
        case = Case(vin="VIN_PENDING_TRAIL", status="pending_claim", originating_camera_id=2)
        db.add(case)
        db.commit()
        db.refresh(case)

        scan = Scan(
            camera_id=2,
            plate="PEND01",
            vin="VIN_PENDING_TRAIL",
            latitude=35.0,
            longitude=-80.0,
            scanned_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        )
        db.add(scan)
        db.commit()

        resp = client.get(f"/api/v1/cases/{case.id}/scans", headers=alice_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["plate"] == "PEND01"

    def test_cross_tenant_active_case_access_denied(self, client, users, cameras, db, bob_headers):
        """Bob (Tenant B) CANNOT access Alice's (Tenant A) active case scan history."""
        case_a = Case(vin="VIN_ALICE_SECRET", status="active", tenant_id=1, assigned_agent_id=1)
        db.add(case_a)
        db.commit()
        db.refresh(case_a)

        # Bob attempts to access Alice's case scans by guessing case_id
        resp = client.get(f"/api/v1/cases/{case_a.id}/scans", headers=bob_headers)
        assert resp.status_code == 404  # 404 prevents leaking case existence

    def test_cross_tenant_closed_case_access_denied(self, client, users, cameras, db, bob_headers):
        """Bob CANNOT access Alice's closed case scans."""
        case_a = Case(vin="VIN_ALICE_CLOSED", status="closed", tenant_id=1, assigned_agent_id=1)
        db.add(case_a)
        db.commit()
        db.refresh(case_a)

        resp = client.get(f"/api/v1/cases/{case_a.id}/scans", headers=bob_headers)
        assert resp.status_code == 404

    def test_unauthenticated_requests_rejected(self, client, active_case_a):
        """Unauthenticated requests to protected endpoints return 401."""
        r1 = client.get("/api/v1/cases")
        assert r1.status_code == 401

        r2 = client.post(f"/api/v1/cases/{active_case_a.id}/claim")
        assert r2.status_code == 401

        r3 = client.get(f"/api/v1/cases/{active_case_a.id}/scans")
        assert r3.status_code == 401


class TestAuthLogin:
    """Authentication login endpoint tests."""

    def test_login_success(self, client, users):
        """Valid credentials return a JWT token and user info."""
        resp = client.post("/api/v1/auth/login", json={"username": "alice", "password": "alice123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "alice"
        assert data["tenant_id"] == 1
        assert data["tenant_name"] == "Acme Recovery"
        assert data["role"] == "admin"

    def test_login_invalid_password(self, client, users):
        """Wrong password returns 401."""
        resp = client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrongpassword"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client, users):
        """Nonexistent username returns 401."""
        resp = client.post("/api/v1/auth/login", json={"username": "nonexistent", "password": "password"})
        assert resp.status_code == 401
