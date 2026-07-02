"""
Project ICARUS — Setup Script
==============================
Run from the scripts/ folder:
    python create_project.py

Generates the complete ICARUS directory structure,
creates all files, and adds __init__.py to every
Python package automatically.
"""

from pathlib import Path
import json
import sys

# ── Resolve base path ─────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
print(f"\n📁 Creating ICARUS structure at: {BASE}\n")

# ══════════════════════════════════════════════════════════════════
# DIRECTORIES
# ══════════════════════════════════════════════════════════════════
directories = [
    # API
    "backend/app/api/v1",

    # Brain
    "backend/app/brain",

    # LLM abstraction layer
    "backend/app/llm",

    # Voice — STT, TTS, wake word, language layer
    "backend/app/voice/language",

    # Personality engine + JSON profiles
    "backend/app/personality/profiles",

    # Context engine
    "backend/app/context/detectors",

    # Memory — short-term, long-term, vector
    "backend/app/memory",

    # RAG engine + document loaders
    "backend/app/rag/loaders",

    # Tool plugin system
    "backend/app/tools/github",
    "backend/app/tools/music",
    "backend/app/tools/browser",
    "backend/app/tools/code",
    "backend/app/tools/weather",
    "backend/app/tools/filesystem",

    # Config — all settings in one place
    "backend/app/config",

    # Core — shared utilities
    "backend/app/core",

    # Events — decoupled event bus
    "backend/app/events",

    # Pydantic schemas — request/response models
    "backend/app/schemas",

    # Frontend (Phase 3 — React + TypeScript)
    "frontend/src",

    # Documentation
    "docs",

    # Tests
    "tests/unit/brain",
    "tests/unit/voice",
    "tests/unit/tools",
    "tests/unit/memory",
    "tests/integration",

    # Docker
    "docker",

    # GitHub Actions CI
    ".github/workflows",

    # Requirements split by environment
    "requirements",

    # Utility scripts
    "scripts",
]

# ══════════════════════════════════════════════════════════════════
# FILES
# ══════════════════════════════════════════════════════════════════
files = [

    # ── API ──────────────────────────────────────────────────────
    "backend/app/api/__init__.py",
    "backend/app/api/v1/__init__.py",
    "backend/app/api/v1/chat.py",
    "backend/app/api/v1/voice.py",
    "backend/app/api/v1/health.py",
    "backend/app/api/v1/memory.py",

    # ── Brain ────────────────────────────────────────────────────
    "backend/app/brain/__init__.py",
    "backend/app/brain/orchestrator.py",
    "backend/app/brain/intent_router.py",
    "backend/app/brain/planner.py",

    # ── LLM Manager ──────────────────────────────────────────────
    "backend/app/llm/__init__.py",
    "backend/app/llm/base.py",          # Abstract LLMProvider interface
    "backend/app/llm/gemini.py",        # Gemini 1.5 Flash
    "backend/app/llm/claude.py",        # Future — Claude
    "backend/app/llm/ollama.py",        # Future — local models
    "backend/app/llm/manager.py",       # Swap providers here

    # ── Voice ────────────────────────────────────────────────────
    "backend/app/voice/__init__.py",
    "backend/app/voice/stt.py",         # Whisper large-v3
    "backend/app/voice/tts.py",         # ElevenLabs + cloned voice
    "backend/app/voice/wake_word.py",   # Porcupine
    "backend/app/voice/language/__init__.py",
    "backend/app/voice/language/detector.py",
    "backend/app/voice/language/normalizer.py",
    "backend/app/voice/language/slang_map.py",  # Indian slang dictionary

    # ── Personality ──────────────────────────────────────────────
    "backend/app/personality/__init__.py",
    "backend/app/personality/manager.py",
    "backend/app/personality/prompt_builder.py",
    "backend/app/personality/profiles/developer.json",
    "backend/app/personality/profiles/bro.json",
    "backend/app/personality/profiles/mentor.json",
    "backend/app/personality/profiles/night_owl.json",
    "backend/app/personality/profiles/coach.json",
    "backend/app/personality/profiles/minimalist.json",

    # ── Context engine ───────────────────────────────────────────
    "backend/app/context/__init__.py",
    "backend/app/context/engine.py",
    "backend/app/context/detectors/__init__.py",
    "backend/app/context/detectors/app_detector.py",
    "backend/app/context/detectors/time_detector.py",

    # ── Memory ───────────────────────────────────────────────────
    "backend/app/memory/__init__.py",
    "backend/app/memory/short_term.py",     # Current conversation
    "backend/app/memory/long_term.py",      # User prefs + history
    "backend/app/memory/vector_store.py",   # Qdrant semantic memory

    # ── RAG ──────────────────────────────────────────────────────
    "backend/app/rag/__init__.py",
    "backend/app/rag/ingestion.py",
    "backend/app/rag/retriever.py",
    "backend/app/rag/loaders/__init__.py",
    "backend/app/rag/loaders/pdf.py",
    "backend/app/rag/loaders/markdown.py",
    "backend/app/rag/loaders/web.py",
    "backend/app/rag/loaders/docx.py",
    "backend/app/rag/loaders/git.py",

    # ── Tools ────────────────────────────────────────────────────
    "backend/app/tools/__init__.py",
    "backend/app/tools/base.py",        # BaseTool interface
    "backend/app/tools/registry.py",    # Auto-discovers all tools
    "backend/app/tools/github/__init__.py",
    "backend/app/tools/github/tool.py",
    "backend/app/tools/music/__init__.py",
    "backend/app/tools/music/tool.py",
    "backend/app/tools/browser/__init__.py",
    "backend/app/tools/browser/tool.py",
    "backend/app/tools/code/__init__.py",
    "backend/app/tools/code/tool.py",
    "backend/app/tools/weather/__init__.py",
    "backend/app/tools/weather/tool.py",
    "backend/app/tools/filesystem/__init__.py",
    "backend/app/tools/filesystem/tool.py",

    # ── Config ───────────────────────────────────────────────────
    "backend/app/config/__init__.py",
    "backend/app/config/settings.py",   # pydantic-settings BaseSettings
    "backend/app/config/logging.py",    # Structured logging setup
    "backend/app/config/constants.py",  # App-wide constants

    # ── Core ─────────────────────────────────────────────────────
    "backend/app/core/__init__.py",
    "backend/app/core/exceptions.py",   # Custom exception hierarchy
    "backend/app/core/dependencies.py", # FastAPI dependency injection
    "backend/app/core/security.py",     # Auth, rate limiting

    # ── Events ───────────────────────────────────────────────────
    "backend/app/events/__init__.py",
    "backend/app/events/bus.py",         # Central event dispatcher
    "backend/app/events/events.py",      # Event type definitions
    "backend/app/events/subscribers.py", # Event handlers

    # ── Schemas ──────────────────────────────────────────────────
    "backend/app/schemas/__init__.py",
    "backend/app/schemas/chat.py",
    "backend/app/schemas/voice.py",
    "backend/app/schemas/memory.py",
    "backend/app/schemas/tool.py",

    # ── Backend root ─────────────────────────────────────────────
    "backend/main.py",
    "backend/__init__.py",

    # ── Docs ─────────────────────────────────────────────────────
    "docs/IDD-001-voice-engine.md",
    "docs/IDD-002-personality-engine.md",
    "docs/IDD-003-tool-engine.md",
    "docs/IDD-004-rag-engine.md",
    "docs/IDD-005-memory-system.md",
    "docs/ADR-001-qdrant-over-chroma.md",
    "docs/ADR-002-fastapi-over-flask.md",
    "docs/ADR-003-intent-router-before-llm.md",
    "docs/architecture.md",
    "docs/roadmap.md",
    "docs/coding-standards.md",
    "docs/contributing.md",

    # ── Tests ────────────────────────────────────────────────────
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/unit/__init__.py",
    "tests/unit/brain/__init__.py",
    "tests/unit/brain/test_intent_router.py",
    "tests/unit/voice/__init__.py",
    "tests/unit/voice/test_language_detector.py",
    "tests/unit/tools/__init__.py",
    "tests/unit/tools/test_tool_registry.py",
    "tests/unit/memory/__init__.py",
    "tests/unit/memory/test_short_term.py",
    "tests/integration/__init__.py",
    "tests/integration/test_chat_flow.py",

    # ── Docker ───────────────────────────────────────────────────
    "docker/Dockerfile.backend",
    "docker/Dockerfile.frontend",
    "docker/.dockerignore",

    # ── CI ───────────────────────────────────────────────────────
    ".github/workflows/ci.yml",

    # ── Requirements ─────────────────────────────────────────────
    "requirements/base.txt",
    "requirements/dev.txt",
    "requirements/prod.txt",

    # ── Root ─────────────────────────────────────────────────────
    "docker-compose.yml",
    ".env.example",
    ".gitignore",
    "LICENSE",
    "README.md",
    "scripts/create_project.py",
    "scripts/seed_personalities.py",
    "scripts/test_voice.py",
]

# ══════════════════════════════════════════════════════════════════
# PERSONALITY PROFILE CONTENT — real JSON, not empty files
# ══════════════════════════════════════════════════════════════════
personality_profiles = {
    "developer.json": {
        "name": "Developer",
        "description": "Analytical, precise, code-focused. Activates when VS Code or terminal is open.",
        "humor": 20,
        "sarcasm": 10,
        "confidence": 90,
        "verbosity": "medium",
        "emoji": False,
        "slang": False,
        "hinglish": False,
        "voice_speed": 1.0,
        "thinking_style": "analytical",
        "triggers": ["vscode", "terminal", "pycharm", "cursor"],
        "greeting": "Ready. What are we building?",
        "tone_adjectives": ["precise", "direct", "technical"]
    },
    "bro.json": {
        "name": "Bro",
        "description": "Casual, Hinglish-friendly, desi daily companion. Default personality.",
        "humor": 75,
        "sarcasm": 30,
        "confidence": 85,
        "verbosity": "low",
        "emoji": False,
        "slang": True,
        "hinglish": True,
        "voice_speed": 1.05,
        "thinking_style": "casual",
        "triggers": ["discord", "spotify", "youtube", "default"],
        "greeting": "Haan bhai, bol kya scene hai?",
        "tone_adjectives": ["warm", "casual", "desi", "relatable"]
    },
    "mentor.json": {
        "name": "Mentor",
        "description": "Patient, teaching-focused, encourages understanding over answers.",
        "humor": 35,
        "sarcasm": 0,
        "confidence": 80,
        "verbosity": "high",
        "emoji": False,
        "slang": False,
        "hinglish": False,
        "voice_speed": 0.95,
        "thinking_style": "pedagogical",
        "triggers": ["notion", "obsidian", "anki", "browser"],
        "greeting": "What would you like to understand today?",
        "tone_adjectives": ["patient", "clear", "encouraging"]
    },
    "night_owl.json": {
        "name": "Night owl",
        "description": "Chill, low-energy, late-night companion. Activates after 10 PM.",
        "humor": 50,
        "sarcasm": 20,
        "confidence": 70,
        "verbosity": "low",
        "emoji": False,
        "slang": True,
        "hinglish": True,
        "voice_speed": 0.92,
        "thinking_style": "relaxed",
        "triggers": ["time:22", "time:23", "time:00", "time:01"],
        "greeting": "Raat ko jaag rahe ho phir... kya chal raha hai?",
        "tone_adjectives": ["calm", "mellow", "chill"]
    },
    "coach.json": {
        "name": "Coach",
        "description": "Motivating, goal-oriented, pushes you to do your best.",
        "humor": 30,
        "sarcasm": 5,
        "confidence": 95,
        "verbosity": "medium",
        "emoji": False,
        "slang": False,
        "hinglish": True,
        "voice_speed": 1.1,
        "thinking_style": "motivational",
        "triggers": ["leetcode", "gym", "notion", "goals"],
        "greeting": "Let's get to work. What's the goal today?",
        "tone_adjectives": ["energetic", "focused", "direct"]
    },
    "minimalist.json": {
        "name": "Minimalist",
        "description": "Ultra concise. One sentence maximum per response unless asked for more.",
        "humor": 10,
        "sarcasm": 0,
        "confidence": 95,
        "verbosity": "minimal",
        "emoji": False,
        "slang": False,
        "hinglish": False,
        "voice_speed": 1.0,
        "thinking_style": "minimal",
        "triggers": [],
        "greeting": "Ready.",
        "tone_adjectives": ["terse", "precise", "clean"]
    }
}

# ══════════════════════════════════════════════════════════════════
# FILE STUBS — minimal but meaningful starting content
# ══════════════════════════════════════════════════════════════════
file_stubs = {
    "backend/main.py": '''\
"""
ICARUS — Entry point
"""
from fastapi import FastAPI
from app.api.v1 import chat, voice, health

app = FastAPI(
    title="Project ICARUS",
    description="AI Operating System",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router,   prefix="/api/v1")
app.include_router(voice.router,  prefix="/api/v1")
''',

    "backend/app/api/v1/health.py": '''\
from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {"status": "online", "system": "ICARUS", "version": "0.1.0"}
''',

    "backend/app/tools/base.py": '''\
"""
BaseTool — every ICARUS tool implements this interface.
Adding a new tool = create a new folder, implement BaseTool, done.
The brain never knows which tool it calls — just execute().
"""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any

class ToolResult(BaseModel):
    success: bool
    output: Any
    message: str
    tool_name: str

class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier e.g. \'github\', \'music\', \'browser\'"""

    @property
    @abstractmethod
    def description(self) -> str:
        """One line — what this tool does"""

    @property
    @abstractmethod
    def triggers(self) -> list[str]:
        """Intent keywords that route to this tool"""

    @abstractmethod
    async def execute(self, input: str, context: dict) -> ToolResult:
        """Run the tool. Always returns ToolResult."""
''',

    "backend/app/events/events.py": '''\
"""
ICARUS Event definitions.
Components communicate through events — not direct calls.

Flow example:
  User speaks → SpeechRecognizedEvent → Brain
  Brain responds → ResponseGeneratedEvent → Voice Engine
"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IcarusEvent:
    timestamp: datetime = None
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

@dataclass
class SpeechRecognizedEvent(IcarusEvent):
    text: str = ""
    language: str = "en"
    confidence: float = 1.0

@dataclass
class IntentDetectedEvent(IcarusEvent):
    intent: str = ""
    raw_input: str = ""
    tool: str = None

@dataclass
class ResponseGeneratedEvent(IcarusEvent):
    text: str = ""
    language: str = "en"
    personality: str = "bro"

@dataclass
class ToolExecutedEvent(IcarusEvent):
    tool_name: str = ""
    success: bool = True
    output: str = ""
''',

    "backend/app/core/exceptions.py": '''\
"""
ICARUS custom exception hierarchy.
Catch IcarusError to handle all ICARUS-specific errors.
"""

class IcarusError(Exception):
    """Base exception for all ICARUS errors."""

class LLMError(IcarusError):
    """LLM provider failed or returned unexpected output."""

class ToolError(IcarusError):
    """A tool failed during execution."""

class MemoryError(IcarusError):
    """Memory read/write failed."""

class VoiceError(IcarusError):
    """STT or TTS failed."""

class ConfigError(IcarusError):
    """Missing or invalid configuration."""
''',

    ".env.example": '''\
# ── LLM ──────────────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini          # gemini | claude | ollama

# ── Voice ────────────────────────────────────────────────────────
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=your_cloned_voice_id_here
ELEVENLABS_MODEL=eleven_multilingual_v2
PICOVOICE_KEY=your_picovoice_key_here

# ── GitHub tool ──────────────────────────────────────────────────
GITHUB_TOKEN=your_github_pat_here
GITHUB_USERNAME=zayyydh

# ── Database ─────────────────────────────────────────────────────
POSTGRES_URL=postgresql://icarus:icarus@localhost:5432/icarus
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379

# ── App ──────────────────────────────────────────────────────────
ICARUS_ENV=development       # development | production
ICARUS_VERSION=0.1.0
LOG_LEVEL=INFO
''',

    ".gitignore": '''\
# Python
__pycache__/
*.py[cod]
*.pyo
.Python
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/
env/

# Environment
.env
*.env

# Data
data/
*.db
*.sqlite

# Models (large files)
*.pt
*.bin
*.onnx

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Docker volumes
postgres_data/
qdrant_data/
redis_data/

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Logs
*.log
logs/
''',

    "requirements/base.txt": '''\
# LLM
google-generativeai==0.5.4
anthropic==0.25.0

# API
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1

# Voice
openai-whisper==20231117
pyaudio==0.2.14
pygame==2.5.2
pvporcupine==3.0.2
elevenlabs==1.3.0

# Embeddings + Vector store
sentence-transformers==2.7.0
qdrant-client==1.9.1

# Language detection
langdetect==1.0.9

# RAG / Document loading
pypdf==4.2.0
python-docx==1.1.0
beautifulsoup4==4.12.3
httpx==0.27.0

# Browser automation
playwright==1.44.0

# GitHub
PyGithub==2.3.0

# Database
sqlalchemy==2.0.30
asyncpg==0.29.0
redis==5.0.4

# Utilities
python-dotenv==1.0.1
numpy==1.26.4
''',

    "requirements/dev.txt": '''\
-r base.txt

# Testing
pytest==8.2.0
pytest-asyncio==0.23.6
pytest-cov==5.0.0
httpx==0.27.0

# Linting + formatting
ruff==0.4.4
mypy==1.10.0
''',

    "docker-compose.yml": '''\
version: "3.9"

services:

  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - qdrant
      - redis
    volumes:
      - ./backend:/app/backend

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: icarus
      POSTGRES_PASSWORD: icarus
      POSTGRES_DB: icarus
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
''',

    "docker/Dockerfile.backend": '''\
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    portaudio19-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY backend/ ./backend/
COPY .env.example .env

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
''',

    ".github/workflows/ci.yml": '''\
name: ICARUS CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: pip install -r requirements/dev.txt

      - name: Lint with Ruff
        run: ruff check backend/

      - name: Type check with mypy
        run: mypy backend/app --ignore-missing-imports

      - name: Run tests
        run: pytest tests/ -v --cov=backend/app --cov-report=term
''',
}

# ══════════════════════════════════════════════════════════════════
# CREATE EVERYTHING
# ══════════════════════════════════════════════════════════════════

created_dirs  = 0
created_files = 0
skipped       = 0

# 1. Directories
for d in directories:
    path = BASE / d
    path.mkdir(parents=True, exist_ok=True)
    created_dirs += 1

# 2. Files
for f in files:
    path = BASE / f
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Personality JSON files
        filename = path.name
        if filename in personality_profiles:
            path.write_text(
                json.dumps(personality_profiles[filename], indent=2),
                encoding="utf-8"
            )
        # Files with stub content
        elif str(path.relative_to(BASE)).replace("\\", "/") in file_stubs:
            key = str(path.relative_to(BASE)).replace("\\", "/")
            path.write_text(file_stubs[key], encoding="utf-8")
        else:
            path.touch()
        created_files += 1
    else:
        skipped += 1

# 3. __init__.py in every Python package under backend/
for py_dir in (BASE / "backend").rglob("*"):
    if py_dir.is_dir():
        init = py_dir / "__init__.py"
        if not init.exists():
            init.touch()
            created_files += 1

# ══════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════
print("=" * 55)
print("  🚀  Project ICARUS — structure created successfully!")
print("=" * 55)
print(f"  📁  Directories : {created_dirs}")
print(f"  📄  Files       : {created_files}")
print(f"  ⏭️   Skipped     : {skipped} (already existed)")
print("=" * 55)
print("\n  Next steps:")
print("  1.  cd .. && git init && git checkout -b develop")
print("  2.  git add . && git commit -m 'chore: initial ICARUS structure'")
print("  3.  Create repo on GitHub: zayyydh/ICARUS")
print("  4.  git remote add origin https://github.com/zayyydh/ICARUS.git")
print("  5.  git push -u origin develop")
print("\n  Then come back — we write README.md together. 🔥\n")