"""
ICARUS Health + Context endpoints
===================================
GET /api/v1/health          → liveness
GET /api/v1/health/ready    → full system status
GET /api/v1/health/context  → current context snapshot
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone

from app.config.settings import settings
from app.config.constants import ICARUS_NAME

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str
    system:    str
    version:   str
    timestamp: str

class ReadinessResponse(BaseModel):
    status:              str
    system:              str
    version:             str
    environment:         str
    llm_provider:        str
    default_personality: str
    default_language:    str
    timestamp:           str

class ContextResponse(BaseModel):
    hour:         int
    active_apps:  list[str]
    personality:  str
    reason:       str
    auto_switch:  bool


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="online",
        system=ICARUS_NAME,
        version=settings.ICARUS_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness check")
async def readiness_check() -> ReadinessResponse:
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


@router.get("/health/context", response_model=ContextResponse, summary="Context snapshot")
async def context_check() -> ContextResponse:
    """
    Shows what ICARUS currently detects about your environment.
    Useful for debugging personality auto-switching.
    Visit this in your browser to see what apps ICARUS sees.
    """
    from app.context.engine import context_engine
    snapshot = await context_engine.detect()
    return ContextResponse(
        hour=snapshot.hour,
        active_apps=snapshot.active_apps,
        personality=snapshot.personality,
        reason=snapshot.reason,
        auto_switch=settings.PERSONALITY_AUTO_SWITCH,
    )