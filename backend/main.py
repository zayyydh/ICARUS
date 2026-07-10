"""
ICARUS — Entry point
=====================
Updated to include chat router and LLM health check.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.logging import setup_logging, log_boot
from app.config.settings import settings
from app.config.constants import (
    API_V1_PREFIX,
    API_TITLE,
    API_DESCRIPTION,
    DEV_CORS_ORIGINS,
)
from app.api.v1 import health, chat

setup_logging()
logger = logging.getLogger("icarus.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    log_boot()

    # Verify LLM is reachable on startup
    from app.llm.manager import llm
    logger.info("Checking LLM connection...")
    ok = await llm.health_check()
    if ok:
        logger.info(
            "LLM connection verified",
            extra={"provider": llm.provider_name, "model": llm.model_name}
        )
    else:
        logger.warning(
            "LLM health check failed — check your API key",
            extra={"provider": llm.provider_name}
        )

    logger.info("ICARUS API server ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────────
    logger.info("ICARUS shutting down. Goodbye.")


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=settings.ICARUS_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_CORS_ORIGINS if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(chat.router,   prefix=API_V1_PREFIX)
# app.include_router(voice.router, prefix=API_V1_PREFIX)  ← Sprint 3