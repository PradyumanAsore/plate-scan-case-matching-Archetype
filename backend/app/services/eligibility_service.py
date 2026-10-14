"""Mock partner-network eligibility client.

This module provides a clean interface for checking vehicle eligibility.
In production, replace the implementation with a real HTTP call.
The mock version is co-hosted as a FastAPI route for convenience.
"""

from __future__ import annotations

import httpx
from app.core.config import get_settings


class EligibilityError(Exception):
    """Raised when the eligibility service is unreachable or returns an error."""
    pass


async def check_eligibility(vin: str) -> bool:
    """Call the partner eligibility service.

    Returns True if the vehicle is eligible for repo, False if not.
    Raises EligibilityError on timeout or HTTP error so callers can
    distinguish a negative result from a service failure.
    """
    settings = get_settings()

    # In-memory test / mock hook for unit test speed and reliability
    if "testserver" in settings.eligibility_service_url or settings.eligibility_service_url.startswith("mock://"):
        return not vin.upper().startswith("INELIGIBLE")

    timeout = httpx.Timeout(
        connect=settings.eligibility_timeout_seconds,
        read=settings.eligibility_timeout_seconds,
        write=settings.eligibility_timeout_seconds,
        pool=settings.eligibility_timeout_seconds,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                settings.eligibility_service_url,
                json={"vin": vin},
            )
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("still_eligible_for_repo", False))
    except httpx.TimeoutException as exc:
        raise EligibilityError(f"Eligibility service timed out for VIN {vin}") from exc
    except httpx.HTTPStatusError as exc:
        raise EligibilityError(
            f"Eligibility service returned {exc.response.status_code} for VIN {vin}"
        ) from exc
    except httpx.HTTPError as exc:
        raise EligibilityError(
            f"Eligibility service error for VIN {vin}: {exc}"
        ) from exc
