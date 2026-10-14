"""Core configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://platescan:changeme_in_production@localhost:5432/platescan"

    # JWT
    jwt_secret_key: str = "changeme_use_openssl_rand_hex_32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # CORS
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Eligibility service
    eligibility_service_url: str = "http://localhost:8000/mock/partner-network/eligibility"
    eligibility_timeout_seconds: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
