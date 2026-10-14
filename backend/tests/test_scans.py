"""Tests for POST /api/v1/scans — scan ingestion endpoint."""

import pytest


class TestScanIngestion:
    """Scan ingestion: camera resolution, case matching, eligibility."""

    def test_valid_scan_existing_case(self, client, users, cameras, active_case_a):
        """Scan for VIN with an existing active case associates with that case."""
        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_1001",
            "plate": "7XYZ123",
            "vin": "1FTFW1E51NFA12345",
            "latitude": 33.749,
            "longitude": -84.388,
            "scanned_at": "2026-09-01T14:32:00Z",
            "image_url": "https://example.com/scans/img_new.jpg",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["scan_id"] is not None
        assert data["case_id"] == 1
        assert data["case_status"] == "active"
        assert "existing case" in data["message"].lower()

    def test_valid_scan_eligible_vin_creates_pending_case(self, client, users, cameras):
        """Scan for a new eligible VIN creates a pending_claim case."""
        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_2050",
            "plate": "ABC9999",
            "vin": "5NPE34AF9KH123456",
            "latitude": 34.05,
            "longitude": -118.24,
            "scanned_at": "2026-09-10T10:00:00Z",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["case_id"] is not None
        assert data["case_status"] == "pending_claim"

    def test_valid_scan_ineligible_vin_no_case(self, client, users, cameras):
        """Scan for an ineligible VIN stores the scan but creates no case."""
        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_1001",
            "plate": "NOCASE1",
            "vin": "INELIGIBLE_VIN_001",
            "latitude": 33.0,
            "longitude": -84.0,
            "scanned_at": "2026-09-10T12:00:00Z",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["scan_id"] is not None
        assert data["case_id"] is None
        assert "not eligible" in data["message"].lower()

    def test_unknown_camera_rejected(self, client, users, cameras):
        """Scan from an unknown camera_id returns 404."""
        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_unknown",
            "plate": "TEST123",
            "vin": "SOMEVIN123",
            "latitude": 0, "longitude": 0,
            "scanned_at": "2026-01-01T00:00:00Z",
        })
        assert resp.status_code == 404

    def test_inactive_camera_rejected(self, client, users, cameras):
        """Scan from an inactive camera returns 422."""
        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_9999",
            "plate": "TEST123",
            "vin": "SOMEVIN123",
            "latitude": 0, "longitude": 0,
            "scanned_at": "2026-01-01T00:00:00Z",
        })
        assert resp.status_code == 422

    def test_duplicate_scan_no_duplicate_case(self, client, users, cameras):
        """Two scans for the same eligible VIN don't create two pending cases."""
        payload = {
            "camera_id": "cam_1001",
            "plate": "DUP123",
            "vin": "UNIQUEVIN12345",
            "latitude": 33.0, "longitude": -84.0,
            "scanned_at": "2026-09-10T12:00:00Z",
        }
        r1 = client.post("/api/v1/scans", json=payload)
        assert r1.status_code == 201
        case_id_1 = r1.json()["case_id"]

        # Second scan — should match the existing pending case
        payload["scanned_at"] = "2026-09-10T12:01:00Z"
        r2 = client.post("/api/v1/scans", json=payload)
        assert r2.status_code == 201
        case_id_2 = r2.json()["case_id"]

        assert case_id_1 == case_id_2

    def test_scan_persisted_on_eligibility_timeout(self, client, users, cameras, monkeypatch):
        """If eligibility service fails, scan is still stored."""
        from app.services import eligibility_service

        async def mock_fail(vin):
            raise eligibility_service.EligibilityError("timeout")

        monkeypatch.setattr(eligibility_service, "check_eligibility", mock_fail)

        resp = client.post("/api/v1/scans", json={
            "camera_id": "cam_1001",
            "plate": "FAIL123",
            "vin": "TIMEOUTVIN123",
            "latitude": 33.0, "longitude": -84.0,
            "scanned_at": "2026-09-10T13:00:00Z",
        })
        assert resp.status_code == 502
        assert "eligibility check failed" in resp.json()["detail"].lower()

    def test_invalid_payload_rejected(self, client, users, cameras):
        """Missing required fields returns 422 validation error."""
        resp = client.post("/api/v1/scans", json={"camera_id": "cam_1001"})
        assert resp.status_code == 422
