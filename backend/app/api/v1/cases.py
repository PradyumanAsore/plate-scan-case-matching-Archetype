"""Cases router — list, claim, scan history (all authenticated)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.case import CaseClaimResponse, CaseListResponse, CaseResponse
from app.schemas.scan import ScanResponse
from app.services.case_service import (
    CaseServiceError,
    claim_case,
    close_case,
    get_case_with_access_check,
    get_scans_for_case,
    list_cases,
)

router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.get("/cases", response_model=CaseListResponse)
def list_cases_endpoint(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(None, description="Filter by case status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List cases visible to the authenticated user.

    Returns own tenant's cases (any status) plus globally claimable pending_claim cases.
    """
    items, total = list_cases(db, user, status_filter=status, limit=limit, offset=offset)
    return CaseListResponse(
        items=[
            CaseResponse(
                id=c.id,
                vin=c.vin,
                status=c.status,
                tenant_id=c.tenant_id,
                tenant_name=c.tenant.name if c.tenant else None,
                assigned_agent_id=c.assigned_agent_id,
                assigned_agent_username=(
                    c.assigned_agent.username if c.assigned_agent else None
                ),
                originating_camera_id=c.originating_camera_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/cases/{case_id}/claim", response_model=CaseClaimResponse)
def claim_case_endpoint(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Claim a pending_claim case for the authenticated user's tenant.

    Atomically sets status to 'active' and assigns the tenant and agent.
    Returns 409 if already claimed or closed.
    """
    try:
        case = claim_case(db, case_id, user)
    except CaseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return CaseClaimResponse(
        id=case.id,
        vin=case.vin,
        status=case.status,
        tenant_id=case.tenant_id,
        assigned_agent_id=case.assigned_agent_id,
        message="Case successfully claimed.",
    )


@router.post("/cases/{case_id}/close", response_model=CaseClaimResponse)
def close_case_endpoint(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Close an active case owned by the authenticated user's tenant."""
    try:
        case = close_case(db, case_id, user)
    except CaseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return CaseClaimResponse(
        id=case.id,
        vin=case.vin,
        status=case.status,
        tenant_id=case.tenant_id,
        assigned_agent_id=case.assigned_agent_id,
        message="Case closed successfully.",
    )


@router.get("/cases/{case_id}/scans", response_model=list[ScanResponse])
def get_case_scans_endpoint(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Get the full scan trail for a case's VIN.

    Includes sightings from cameras across all tenants, in chronological order.
    """
    try:
        scans = get_scans_for_case(db, case_id, user)
    except CaseServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return [ScanResponse(**s) for s in scans]
