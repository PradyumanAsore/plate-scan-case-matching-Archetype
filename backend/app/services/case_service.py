"""Case service — claiming, listing, and access control.

Key design decisions:
- Claiming uses UPDATE ... WHERE with optimistic status check (atomic CAS).
- Listing combines own-tenant cases with globally visible pending_claim cases.
- Access control is row-level: active/closed cases only visible to owning tenant.
"""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.scan import Scan
from app.models.camera import Camera
from app.models.user import User


class CaseServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def claim_case(db: Session, case_id: int, user: User) -> Case:
    """Atomically claim a pending_claim case.

    Uses UPDATE ... WHERE status = 'pending_claim' to prevent races.
    The row is locked by the UPDATE itself — no separate SELECT FOR UPDATE needed
    because we use a conditional update pattern (compare-and-swap).
    """
    rows_updated = (
        db.query(Case)
        .filter(Case.id == case_id, Case.status == "pending_claim")
        .update(
            {
                Case.status: "active",
                Case.tenant_id: user.tenant_id,
                Case.assigned_agent_id: user.id,
            },
            synchronize_session="fetch",
        )
    )
    db.commit()

    if rows_updated == 0:
        # Either case doesn't exist, or it was already claimed/closed
        case = db.query(Case).filter(Case.id == case_id).first()
        if case is None:
            raise CaseServiceError("Case not found", 404)
        if case.status == "active":
            raise CaseServiceError("Case already claimed by another user", 409)
        if case.status == "closed":
            raise CaseServiceError("Case is closed and cannot be claimed", 409)
        raise CaseServiceError("Case is not in a claimable state", 409)

    case = db.query(Case).filter(Case.id == case_id).first()
    return case


def close_case(db: Session, case_id: int, user: User) -> Case:
    """Close an active case owned by the user's tenant."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise CaseServiceError("Case not found", 404)
    if case.tenant_id != user.tenant_id:
        raise CaseServiceError("Case not found", 404)
    if case.status != "active":
        raise CaseServiceError(f"Cannot close a case with status '{case.status}'", 400)

    case.status = "closed"
    db.commit()
    db.refresh(case)
    return case


def get_case_with_access_check(db: Session, case_id: int, user: User) -> Case:
    """Load a case with tenant-scoped access control.

    Rules:
    - pending_claim cases are visible to any authenticated user (for claiming).
    - active/closed cases are visible only to the owning tenant.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise CaseServiceError("Case not found", 404)

    if case.status == "pending_claim":
        return case  # globally visible

    if case.tenant_id != user.tenant_id:
        # Don't reveal existence — return 404
        raise CaseServiceError("Case not found", 404)

    return case


def list_cases(
    db: Session,
    user: User,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Case], int]:
    """List cases visible to the user: own tenant's + global pending_claim.

    Applies optional status filter without bypassing tenant isolation.
    """
    # Build base visibility filter
    visibility = or_(
        Case.tenant_id == user.tenant_id,  # own tenant
        Case.status == "pending_claim",  # globally visible
    )

    query = db.query(Case).filter(visibility)

    if status_filter:
        query = query.filter(Case.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Case.created_at.desc(), Case.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_scans_for_case(db: Session, case_id: int, user: User) -> list[dict]:
    """Return all scans for the VIN tracked by the given case.

    Includes sightings from ANY tenant's cameras.
    Access control is checked via the case itself.
    """
    case = get_case_with_access_check(db, case_id, user)

    scans = (
        db.query(Scan, Camera)
        .join(Camera, Scan.camera_id == Camera.id)
        .filter(Scan.vin == case.vin)
        .order_by(Scan.scanned_at.asc(), Scan.id.asc())
        .all()
    )

    result = []
    for scan, camera in scans:
        result.append(
            {
                "id": scan.id,
                "camera_id": camera.external_id,
                "camera_description": camera.description,
                "tenant_name": None,  # filled below if needed
                "plate": scan.plate,
                "vin": scan.vin,
                "latitude": scan.latitude,
                "longitude": scan.longitude,
                "scanned_at": scan.scanned_at,
                "image_url": scan.image_url,
                "created_at": scan.created_at,
            }
        )
    return result
