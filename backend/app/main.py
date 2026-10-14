"""Plate Scan & Case Matching Service — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.api.v1.auth import router as auth_router
from app.api.v1.scans import router as scans_router
from app.api.v1.cases import router as cases_router
from app.db.base import Base
from app.db.session import engine, SessionLocal
import app.models  # noqa: F401
from app.models.tenant import Tenant
from scripts.seed import seed_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)

    # Automatically populate seed data for local development if empty
    db = SessionLocal()
    try:
        if db.query(Tenant).first() is None:
            seed_db(db)
    except Exception as e:
        print(f"Startup seed notice: {e}")
    finally:
        db.close()

    yield


app = FastAPI(
    title="Plate Scan & Case Matching Service",
    description=(
        "Ingests vehicle plate scans, matches them against recovery cases, "
        "supports cross-tenant case claiming, and provides a tenant-scoped dashboard."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(scans_router)
app.include_router(cases_router)


# ─── Health check ────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ─── Mock Partner Eligibility Service ────────────────────────────────────────

class EligibilityRequest(BaseModel):
    vin: str


class EligibilityResponse(BaseModel):
    vin: str
    still_eligible_for_repo: bool


@app.post(
    "/mock/partner-network/eligibility",
    response_model=EligibilityResponse,
    tags=["mock"],
)
def mock_eligibility(body: EligibilityRequest):
    """Mock partner eligibility endpoint.

    Deterministic logic for easy demonstration:
    - VINs starting with "INELIGIBLE" → not eligible.
    - All other VINs → eligible.

    This keeps both scenarios easy to trigger from tests and demos.
    """
    eligible = not body.vin.upper().startswith("INELIGIBLE")
    return EligibilityResponse(vin=body.vin, still_eligible_for_repo=eligible)
