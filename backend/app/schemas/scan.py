"""Scan request / response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScanCreateRequest(BaseModel):
    """Incoming camera webhook payload."""

    camera_id: str = Field(..., description="External camera identifier, e.g. cam_1001")
    plate: str = Field(..., min_length=1, max_length=20)
    vin: str = Field(..., min_length=5, max_length=20)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    scanned_at: datetime
    image_url: str | None = Field(None, max_length=2048)


class ScanResponse(BaseModel):
    """Single scan sighting."""

    id: int
    camera_id: str
    camera_description: str | None = None
    tenant_name: str | None = None
    plate: str
    vin: str
    latitude: float
    longitude: float
    scanned_at: datetime
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanIngestResponse(BaseModel):
    """Response after processing a scan webhook."""

    scan_id: int
    plate: str
    vin: str
    case_id: int | None = None
    case_status: str | None = None
    message: str
