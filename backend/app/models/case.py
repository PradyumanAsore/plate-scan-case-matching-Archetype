"""Case ORM model.

Business rules:
- pending_claim: tenant_id and assigned_agent_id are NULL. Globally claimable.
- active: both tenant_id and assigned_agent_id must be set. Owned by one tenant.
- closed: retains ownership. Not modifiable via claim.

A partial unique index on (vin) WHERE status IN ('pending_claim', 'active') prevents
duplicate open cases for the same vehicle. Historical closed cases are allowed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    vin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_claim")
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    originating_camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="cases")
    assigned_agent: Mapped["User | None"] = relationship("User", back_populates="assigned_cases")
    originating_camera: Mapped["Camera | None"] = relationship("Camera")

    __table_args__ = (
        # Only one open (pending or active) case per VIN at a time
        Index(
            "ix_cases_vin_open_unique",
            "vin",
            unique=True,
            postgresql_where=(
                # Raw SQL text for partial unique index
                __import__("sqlalchemy").text("status IN ('pending_claim', 'active')")
            ),
            sqlite_where=(
                __import__("sqlalchemy").text("status IN ('pending_claim', 'active')")
            ),
        ),
        # Status must be one of the allowed values
        CheckConstraint(
            "status IN ('pending_claim', 'active', 'closed')",
            name="ck_cases_status",
        ),
        # pending_claim requires NULL tenant and agent
        CheckConstraint(
            "(status != 'pending_claim') OR (tenant_id IS NULL AND assigned_agent_id IS NULL)",
            name="ck_cases_pending_no_owner",
        ),
        # active requires non-NULL tenant and agent
        CheckConstraint(
            "(status != 'active') OR (tenant_id IS NOT NULL AND assigned_agent_id IS NOT NULL)",
            name="ck_cases_active_has_owner",
        ),
        # Lookup by tenant + status + creation time
        Index("ix_cases_tenant_status_created", "tenant_id", "status", "created_at"),
    )
