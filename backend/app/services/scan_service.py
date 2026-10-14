"""Scan ingestion service.

Orchestrates:
1. Camera resolution and validation.
2. Scan persistence.
3. Case matching (existing active case for the same VIN & tenant).
4. Eligibility check via partner service when no active case exists.
5. Pending-case creation for eligible vehicles.

Transaction design:
- The scan is always persisted in a DB transaction BEFORE calling the external
  eligibility service. This ensures scans are never lost.
- The eligibility call happens OUTSIDE the DB transaction to avoid holding locks
  during network I/O.
- If the vehicle is eligible, a second short transaction creates the pending case
  using INSERT ... ON CONFLICT DO NOTHING on the partial unique index to handle
  concurrent duplicate scans safely.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.models.case import Case
from app.models.scan import Scan
from app.schemas.scan import ScanCreateRequest, ScanIngestResponse
from app.services import eligibility_service


class ScanServiceError(Exception):
    """Domain error during scan processing."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def resolve_camera(db: Session, external_id: str) -> Camera:
    """Look up camera by external ID. Raises on unknown or inactive."""
    camera = db.query(Camera).filter(Camera.external_id == external_id).first()
    if camera is None:
        raise ScanServiceError(f"Unknown camera: {external_id}", 404)
    if not camera.is_active:
        raise ScanServiceError(f"Camera {external_id} is inactive", 422)
    return camera


def find_existing_open_case(db: Session, vin: str) -> Case | None:
    """Find any open (pending_claim or active) case for the given VIN."""
    return (
        db.query(Case)
        .filter(Case.vin == vin, Case.status.in_(["pending_claim", "active"]))
        .first()
    )


def persist_scan(db: Session, payload: ScanCreateRequest, camera: Camera) -> Scan:
    """Insert a scan record and commit. Always succeeds for valid inputs."""
    scan = Scan(
        camera_id=camera.id,
        plate=payload.plate,
        vin=payload.vin,
        latitude=payload.latitude,
        longitude=payload.longitude,
        scanned_at=payload.scanned_at,
        image_url=payload.image_url,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def create_pending_case_safe(db: Session, vin: str, camera: Camera) -> Case | None:
    """Attempt to create a pending_claim case.

    Uses PostgreSQL partial unique index conflict target to avoid duplicates
    when concurrent scans for the same VIN race.

    Returns the Case if created, or the existing open case if one already exists.
    """
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        result = db.execute(
            text(
                """
                INSERT INTO cases (vin, status, originating_camera_id, created_at, updated_at)
                VALUES (:vin, 'pending_claim', :cam_id, NOW(), NOW())
                ON CONFLICT (vin) WHERE status IN ('pending_claim', 'active') DO NOTHING
                RETURNING id, status
                """
            ),
            {"vin": vin, "cam_id": camera.id},
        )
        db.commit()
        row = result.fetchone()
        if row is not None:
            return db.query(Case).get(row[0])
        return find_existing_open_case(db, vin)
    else:
        # SQLite / in-memory test dialect
        try:
            new_case = Case(vin=vin, status="pending_claim", originating_camera_id=camera.id)
            db.add(new_case)
            db.commit()
            db.refresh(new_case)
            return new_case
        except Exception:
            db.rollback()
            return find_existing_open_case(db, vin)


async def ingest_scan(db: Session, payload: ScanCreateRequest) -> ScanIngestResponse:
    """Full scan ingestion pipeline. See module docstring for transaction design."""

    # 1. Resolve camera
    camera = resolve_camera(db, payload.camera_id)

    # 2. Persist scan (always, regardless of case outcome)
    scan = persist_scan(db, payload, camera)

    # 3. Check for existing open case for this VIN
    existing_case = find_existing_open_case(db, payload.vin)
    if existing_case is not None:
        return ScanIngestResponse(
            scan_id=scan.id,
            plate=payload.plate,
            vin=payload.vin,
            case_id=existing_case.id,
            case_status=existing_case.status,
            message="Scan recorded; matched existing case.",
        )

    # 4. No open case — call eligibility service (outside DB transaction)
    try:
        eligible = await eligibility_service.check_eligibility(payload.vin)
    except eligibility_service.EligibilityError as exc:
        # Scan is already persisted. Return a recoverable error.
        raise ScanServiceError(
            f"Scan saved (id={scan.id}) but eligibility check failed: {exc}. "
            "Retry or manually review.",
            status_code=502,
        )

    if not eligible:
        return ScanIngestResponse(
            scan_id=scan.id,
            plate=payload.plate,
            vin=payload.vin,
            case_id=None,
            case_status=None,
            message="Scan recorded; vehicle not eligible for recovery.",
        )

    # 5. Eligible — create pending case (race-safe)
    case = create_pending_case_safe(db, payload.vin, camera)
    return ScanIngestResponse(
        scan_id=scan.id,
        plate=payload.plate,
        vin=payload.vin,
        case_id=case.id if case else None,
        case_status=case.status if case else None,
        message="Scan recorded; pending case created for eligible vehicle.",
    )
