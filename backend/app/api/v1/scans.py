"""Scan ingestion router — unauthenticated camera webhook endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.scan import ScanCreateRequest, ScanIngestResponse
from app.services.scan_service import ScanServiceError, ingest_scan

router = APIRouter(prefix="/api/v1", tags=["scans"])


@router.post("/scans", response_model=ScanIngestResponse, status_code=201)
async def create_scan(
    body: ScanCreateRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Ingest a camera scan. Unauthenticated — simulates a camera webhook.

    Production note: This endpoint should be secured with per-camera HMAC
    signatures, API keys, or mTLS. Replay protection (e.g., idempotency keys
    or scan deduplication windows) and rate limiting should also be applied.
    """
    try:
        return await ingest_scan(db, body)
    except ScanServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
