"""Case request / response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CaseResponse(BaseModel):
    """Single case detail."""

    id: int
    vin: str
    status: str
    tenant_id: int | None
    tenant_name: str | None = None
    assigned_agent_id: int | None
    assigned_agent_username: str | None = None
    originating_camera_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseClaimResponse(BaseModel):
    """Response after successfully claiming a case."""

    id: int
    vin: str
    status: str
    tenant_id: int
    assigned_agent_id: int
    message: str


class CaseListResponse(BaseModel):
    """Paginated case listing."""

    items: list[CaseResponse]
    total: int
    limit: int
    offset: int
