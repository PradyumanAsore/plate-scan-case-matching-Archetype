"""Tenant ORM model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    cameras: Mapped[list["Camera"]] = relationship("Camera", back_populates="tenant")
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="tenant")
