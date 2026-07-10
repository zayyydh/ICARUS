"""
ICARUS pytest configuration
============================
1. Adds backend/ to sys.path so tests can import app.*
2. Loads .env from project root before any test runs
3. Sets test-safe defaults for required API keys
"""

import sys
import os
from pathlib import Path

# ── 1. Add backend/ to path ────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "backend"))

# ── 2. Load .env from project root ────────────────────────────────
# pydantic-settings looks for .env relative to CWD by default.
# When pytest runs from ICARUS root this works — but set explicitly
# to be safe regardless of where pytest is invoked from.
env_file = ROOT / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# ── 3. Set test-safe fallbacks for required keys ──────────────────
# Real API keys are never needed for unit tests.
# These placeholders satisfy pydantic validation without making
# any actual API calls — unit tests never hit external services.
os.environ.setdefault("GEMINI_API_KEY",       "test-gemini-key")
os.environ.setdefault("ELEVENLABS_API_KEY",   "test-elevenlabs-key")
os.environ.setdefault("ELEVENLABS_VOICE_ID",  "test-voice-id")
os.environ.setdefault("ICARUS_ENV",           "test")
os.environ.setdefault("LLM_PROVIDER",         "gemini")