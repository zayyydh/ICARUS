"""
ICARUS — Entry point
=====================
Starts the FastAPI server.
Initialises logging, config, and lifespan events.
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
from app.api.v1 import health


# ── Logging — must be first ────────────────────────────────────────
setup_logging()
logger = logging.getLogger("icarus.main")


# ══════════════════════════════════════════════════════════════════
# LIFESPAN — startup and shutdown events
# ══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Add DB connections, model loading, etc. here later.
    """
    # ── Startup ───────────────────────────────────────────────────
    log_boot()
    logger.info("ICARUS API server ready")

    yield   # Server is running

    # ── Shutdown ──────────────────────────────────────────────────
    logger.info("ICARUS shutting down. Goodbye.")


# ══════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=settings.ICARUS_VERSION,
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc at /redoc
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_CORS_ORIGINS if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────
app.include_router(health.router, prefix=API_V1_PREFIX)
# app.include_router(chat.router,  prefix=API_V1_PREFIX)  ← Phase 2
# app.include_router(voice.router, prefix=API_V1_PREFIX)  ← Phase 3