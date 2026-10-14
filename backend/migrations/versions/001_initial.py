"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("username", sa.String(150), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(512), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="staff"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Cameras
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(100), unique=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cameras_external_id", "cameras", ["external_id"], unique=True)

    # Cases
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vin", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_claim"),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("assigned_agent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("originating_camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cases_vin", "cases", ["vin"])
    op.create_index(
        "ix_cases_vin_open_unique",
        "cases",
        ["vin"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending_claim', 'active')"),
    )
    op.create_index(
        "ix_cases_tenant_status_created",
        "cases",
        ["tenant_id", "status", "created_at"],
    )

    # Check constraints for case invariants
    op.execute(
        "ALTER TABLE cases ADD CONSTRAINT ck_cases_status "
        "CHECK (status IN ('pending_claim', 'active', 'closed'))"
    )
    op.execute(
        "ALTER TABLE cases ADD CONSTRAINT ck_cases_pending_no_owner "
        "CHECK ((status != 'pending_claim') OR (tenant_id IS NULL AND assigned_agent_id IS NULL))"
    )
    op.execute(
        "ALTER TABLE cases ADD CONSTRAINT ck_cases_active_has_owner "
        "CHECK ((status != 'active') OR (tenant_id IS NOT NULL AND assigned_agent_id IS NOT NULL))"
    )

    # Scans
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("plate", sa.String(20), nullable=False),
        sa.Column("vin", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("scanned_at", sa.DateTime(), nullable=False),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scans_vin_scanned_at", "scans", ["vin", "scanned_at"])
    op.create_index("ix_scans_camera_scanned_at", "scans", ["camera_id", "scanned_at"])


def downgrade() -> None:
    op.drop_table("scans")
    op.drop_table("cases")
    op.drop_table("cameras")
    op.drop_table("users")
    op.drop_table("tenants")
