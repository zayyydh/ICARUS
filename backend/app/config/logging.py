"""
ICARUS Logging
===============
Structured, colored, consistent logging across every module.

Usage in any module:
    from app.config.logging import get_logger
    logger = get_logger(__name__)
    logger.info("ICARUS is online")
    logger.error("Something went wrong", extra={"tool": "github"})

All logs go to:
    - Console (colored, human-readable in development)
    - logs/icarus.log (JSON, machine-readable in production)
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from app.config.settings import settings
from app.config.constants import ICARUS_NAME, ICARUS_BANNER


# ── Log directory ──────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parents[4] / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "icarus.log"


# ══════════════════════════════════════════════════════════════════
# COLORS — ANSI escape codes for terminal output
# ══════════════════════════════════════════════════════════════════

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Log level colors
    DEBUG   = "\033[36m"    # Cyan
    INFO    = "\033[32m"    # Green
    WARNING = "\033[33m"    # Yellow
    ERROR   = "\033[31m"    # Red
    CRITICAL= "\033[35m"    # Magenta

    # Component colors
    BRAIN   = "\033[34m"    # Blue
    VOICE   = "\033[96m"    # Bright cyan
    TOOL    = "\033[93m"    # Bright yellow
    MEMORY  = "\033[92m"    # Bright green
    LLM     = "\033[95m"    # Bright magenta

LEVEL_COLORS = {
    "DEBUG":    Color.DEBUG,
    "INFO":     Color.INFO,
    "WARNING":  Color.WARNING,
    "ERROR":    Color.ERROR,
    "CRITICAL": Color.CRITICAL,
}

LEVEL_ICONS = {
    "DEBUG":    "·",
    "INFO":     "✓",
    "WARNING":  "⚠",
    "ERROR":    "✗",
    "CRITICAL": "💀",
}


# ══════════════════════════════════════════════════════════════════
# FORMATTERS
# ══════════════════════════════════════════════════════════════════

class IcarusConsoleFormatter(logging.Formatter):
    """
    Human-readable colored formatter for terminal output.
    Used in development.

    Output format:
    12:34:56  ✓  INFO     brain.orchestrator  │  Intent detected: music_play
    12:34:57  ✗  ERROR    tools.github        │  Push failed: auth error
    """

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp — just time, not full datetime (less noise)
        ts = datetime.now().strftime("%H:%M:%S")

        # Level
        level     = record.levelname
        color     = LEVEL_COLORS.get(level, Color.RESET)
        icon      = LEVEL_ICONS.get(level, " ")
        level_str = f"{color}{icon}  {level:<8}{Color.RESET}"

        # Module name — shorten app.brain.orchestrator → brain.orchestrator
        name = record.name.replace("app.", "")
        name_str = f"{Color.DIM}{name:<28}{Color.RESET}"

        # Message
        msg = record.getMessage()

        # Extra fields — shown as key=value pairs
        extras = ""
        skip = {
            "name", "msg", "args", "levelname", "levelno",
            "pathname", "filename", "module", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread",
            "threadName", "processName", "process", "message",
            "taskName",
        }
        extra_parts = [
            f"{Color.DIM}{k}={Color.RESET}{v}"
            for k, v in record.__dict__.items()
            if k not in skip and not k.startswith("_")
        ]
        if extra_parts:
            extras = f"  {Color.DIM}({', '.join(extra_parts)}){Color.RESET}"

        return f"{Color.DIM}{ts}{Color.RESET}  {level_str}  {name_str}  │  {msg}{extras}"


class IcarusJSONFormatter(logging.Formatter):
    """
    Machine-readable JSON formatter for log files.
    Used in production — easy to parse, ship to log aggregators.

    Output (one JSON object per line):
    {"ts": "2025-07-06T12:34:56Z", "level": "INFO", "module": "brain.orchestrator", "msg": "..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        skip = {
            "name", "msg", "args", "levelname", "levelno",
            "pathname", "filename", "module", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread",
            "threadName", "processName", "process", "message",
            "taskName",
        }

        payload: dict[str, Any] = {
            "ts":     datetime.now(timezone.utc).isoformat(),
            "level":  record.levelname,
            "module": record.name.replace("app.", ""),
            "msg":    record.getMessage(),
        }

        # Attach any extra fields
        for k, v in record.__dict__.items():
            if k not in skip and not k.startswith("_"):
                payload[k] = v

        # Attach exception info if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ══════════════════════════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """
    Call once at application startup — in backend/main.py.
    Configures root logger + ICARUS-specific handlers.
    """

    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # ── Root logger ───────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(log_level)

    # Clear any existing handlers (avoid duplicate logs on reload)
    root.handlers.clear()

    # ── Console handler (always on) ───────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)

    if settings.is_development:
        console.setFormatter(IcarusConsoleFormatter())
    else:
        # Plain JSON in production — no colors (they break log shippers)
        console.setFormatter(IcarusJSONFormatter())

    root.addHandler(console)

    # ── Rotating file handler ─────────────────────────────────────
    # Max 10MB per file, keep last 5 files
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(IcarusJSONFormatter())
    root.addHandler(file_handler)

    # ── Silence noisy third-party loggers ─────────────────────────
    for noisy in [
        "httpx",
        "httpcore",
        "uvicorn.access",
        "google.auth",
        "sentence_transformers",
        "urllib3",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── Confirm logging is ready ───────────────────────────────────
    logger = get_logger("config.logging")
    logger.info(
        "Logging initialized",
        extra={
            "level":  settings.LOG_LEVEL,
            "env":    settings.ICARUS_ENV,
            "file":   str(LOG_FILE),
        }
    )


# ══════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger for any ICARUS module.

    Usage:
        logger = get_logger(__name__)
        logger.info("Ready")
        logger.error("Failed", extra={"reason": "timeout"})
    """
    return logging.getLogger(name)


def log_boot() -> None:
    """
    Prints the ICARUS banner and boot message to stdout.
    Called once at startup before the server starts.
    """
    print(ICARUS_BANNER)
    logger = get_logger("icarus")
    logger.info(
        f"{ICARUS_NAME} v{settings.ICARUS_VERSION} starting",
        extra={
            "env":         settings.ICARUS_ENV,
            "llm":         settings.LLM_PROVIDER,
            "personality": settings.DEFAULT_PERSONALITY,
            "language":    settings.DEFAULT_LANGUAGE,
        }
    )