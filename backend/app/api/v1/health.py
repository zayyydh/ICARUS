"""
ICARUS Health endpoint
=======================
The first real API endpoint.
Confirms the server is running and returns system status.

GET /api/v1/health        → basic liveness check
GET /api/v1/health/ready  → full readiness check (config, env)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone

from app.config.settings import settings
from app.config.constants import ICARUS_NAME
from app.config.logging import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


# ── Response schemas ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    system: str
    version: str
    timestamp: str

class ReadinessResponse(BaseModel):
    status: str
    system: str
    version: str
    environment: str
    llm_provider: str
    default_personality: str
    default_language: str
    timestamp: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Returns 200 if ICARUS is running. Used by Docker and load balancers.",
)
async def health_check() -> HealthResponse:
    """
    Basic liveness check.
    If this returns 200, the server is up.
    """
    logger.debug("Health check called")
    return HealthResponse(
        status="online",
        system=ICARUS_NAME,
        version=settings.ICARUS_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Returns full system config — confirms ICARUS is properly configured.",
)
async def readiness_check() -> ReadinessResponse:
    """
    Full readiness check.
    Returns current config so you can confirm everything loaded correctly.
    Useful when first setting up — visit this in your browser to verify.
    """
    logger.info("Readiness check called")
    return ReadinessResponse(
        status="ready",
        system=ICARUS_NAME,
        version=settings.ICARUS_VERSION,
        environment=settings.ICARUS_ENV,
        llm_provider=settings.LLM_PROVIDER,
        default_personality=settings.DEFAULT_PERSONALITY,
        default_language=settings.DEFAULT_LANGUAGE,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )