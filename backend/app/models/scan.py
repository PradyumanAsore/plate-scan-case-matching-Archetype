"""Scan ORM model.

A scan records a raw camera sighting. It is always linked to its originating camera
and never reassigned. Scans are queried by VIN to build the location trail for a case,
regardless of which tenant's camera captured them.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    plate: Mapped[str] = mapped_column(String(20), nullable=False)
    vin: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    camera: Mapped["Camera"] = relationship("Camera", back_populates="scans")

    __table_args__ = (
        Index("ix_scans_vin_scanned_at", "vin", "scanned_at"),
        Index("ix_scans_camera_scanned_at", "camera_id", "scanned_at"),
    )
