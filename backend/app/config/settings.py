"""
ICARUS Configuration
=====================
Single source of truth for all settings.
Uses pydantic-settings — reads from .env automatically.
Type-safe, validated, and documented.

Usage anywhere in the codebase:
    from app.config.settings import settings
    print(settings.GEMINI_API_KEY)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path
from typing import Literal

# ── Resolve project root ───────────────────────────────────────────
# This file lives at backend/app/config/settings.py
# So root is 4 levels up
ROOT_DIR = Path(__file__).resolve().parents[4]


class IcarusSettings(BaseSettings):
    """
    All ICARUS configuration in one place.
    Every value maps directly to a key in .env
    Pydantic validates types and required fields on startup.
    If a required key is missing, ICARUS refuses to start — by design.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",          # Ignore unknown keys in .env
    )

    # ══════════════════════════════════════════════════════════════
    # APP
    # ══════════════════════════════════════════════════════════════

    ICARUS_ENV: Literal["development", "production", "test"] = Field(
        default="development",
        description="Runtime environment"
    )
    ICARUS_VERSION: str = Field(
        default="0.1.0",
        description="ICARUS version string"
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity"
    )

    # ══════════════════════════════════════════════════════════════
    # LLM
    # ══════════════════════════════════════════════════════════════

    LLM_PROVIDER: Literal["gemini", "claude", "ollama"] = Field(
        default="gemini",
        description="Active LLM provider — swap without touching code"
    )
    GEMINI_API_KEY: str = Field(
        description="Google Gemini API key — get from aistudio.google.com"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model name"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="0 = precise, 1 = creative"
    )
    LLM_MAX_TOKENS: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Max tokens per LLM response"
    )

    # ══════════════════════════════════════════════════════════════
    # VOICE — STT (Whisper)
    # ══════════════════════════════════════════════════════════════

    WHISPER_MODEL: Literal[
        "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
    ] = Field(
        default="large-v3",
        description="Whisper model size — large-v3 for best Indian language support"
    )
    WHISPER_DEVICE: Literal["cpu", "cuda"] = Field(
        default="cpu",
        description="Run Whisper on CPU or GPU"
    )
    SILENCE_THRESHOLD: int = Field(
        default=500,
        description="Audio energy below this is treated as silence"
    )
    SILENCE_SECONDS: float = Field(
        default=1.5,
        description="Seconds of silence before ICARUS stops listening"
    )

    # ══════════════════════════════════════════════════════════════
    # VOICE — TTS (ElevenLabs)
    # ══════════════════════════════════════════════════════════════

    ELEVENLABS_API_KEY: str = Field(
        description="ElevenLabs API key — elevenlabs.io"
    )
    ELEVENLABS_VOICE_ID: str = Field(
        description="Your cloned voice ID from ElevenLabs dashboard"
    )
    ELEVENLABS_MODEL: str = Field(
        default="eleven_multilingual_v2",
        description="TTS model — multilingual v2 handles Hindi+English natively"
    )
    VOICE_STABILITY: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="0 = expressive, 1 = consistent"
    )
    VOICE_SIMILARITY_BOOST: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="How closely output matches your cloned voice"
    )
    VOICE_STYLE: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Style exaggeration level"
    )

    # ══════════════════════════════════════════════════════════════
    # VOICE — Wake word (Porcupine)
    # ══════════════════════════════════════════════════════════════

    PICOVOICE_KEY: str = Field(
        default="",
        description="Picovoice access key — picovoice.ai (free tier)"
    )
    WAKE_WORD: str = Field(
        default="jarvis",
        description="Wake word keyword — must be a Porcupine built-in"
    )

    # ══════════════════════════════════════════════════════════════
    # LANGUAGE
    # ══════════════════════════════════════════════════════════════

    DEFAULT_LANGUAGE: Literal["en", "hi", "mr", "ur", "hinglish"] = Field(
        default="hinglish",
        description="Default language for ICARUS responses"
    )
    SUPPORTED_LANGUAGES: list[str] = Field(
        default=["en", "hi", "mr", "ur", "hinglish"],
        description="Languages ICARUS understands and speaks"
    )

    # ══════════════════════════════════════════════════════════════
    # PERSONALITY
    # ══════════════════════════════════════════════════════════════

    DEFAULT_PERSONALITY: Literal[
        "bro", "developer", "mentor", "coach", "night_owl", "minimalist"
    ] = Field(
        default="bro",
        description="Default personality profile — bro is Hinglish-friendly daily mode"
    )
    PERSONALITY_AUTO_SWITCH: bool = Field(
        default=True,
        description="Auto-switch personality based on time and open apps"
    )
    PROFILES_DIR: Path = Field(
        default=ROOT_DIR / "backend" / "app" / "personality" / "profiles",
        description="Directory containing personality JSON files"
    )

    # ══════════════════════════════════════════════════════════════
    # MEMORY
    # ══════════════════════════════════════════════════════════════

    MAX_HISTORY_TURNS: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Conversation turns kept in short-term memory"
    )

    # ══════════════════════════════════════════════════════════════
    # RAG + VECTOR STORE (Qdrant)
    # ══════════════════════════════════════════════════════════════

    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    QDRANT_COLLECTION: str = Field(
        default="icarus_knowledge",
        description="Qdrant collection name for ICARUS knowledge base"
    )
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Local embedding model — runs offline, zero API cost"
    )
    TOP_K_RESULTS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks retrieved per RAG query"
    )
    CHUNK_SIZE: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Document chunk size in tokens"
    )
    CHUNK_OVERLAP: int = Field(
        default=64,
        ge=0,
        le=256,
        description="Overlap between consecutive chunks"
    )

    # ══════════════════════════════════════════════════════════════
    # DATABASE (PostgreSQL)
    # ══════════════════════════════════════════════════════════════

    POSTGRES_URL: str = Field(
        default="postgresql://icarus:icarus@localhost:5432/icarus",
        description="PostgreSQL connection string for conversation memory"
    )

    # ══════════════════════════════════════════════════════════════
    # CACHE (Redis)
    # ══════════════════════════════════════════════════════════════

    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for session and tool result caching"
    )

    # ══════════════════════════════════════════════════════════════
    # TOOLS
    # ══════════════════════════════════════════════════════════════

    GITHUB_TOKEN: str = Field(
        default="",
        description="GitHub Personal Access Token — repo + workflow scopes"
    )
    GITHUB_USERNAME: str = Field(
        default="zayyydh",
        description="Your GitHub username"
    )
    MAX_SEARCH_RESULTS: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of web search results to retrieve"
    )

    # ══════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES (not from .env — derived at runtime)
    # ══════════════════════════════════════════════════════════════

    @property
    def is_development(self) -> bool:
        return self.ICARUS_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.ICARUS_ENV == "production"

    @property
    def debug(self) -> bool:
        return self.ICARUS_ENV == "development"

    # ══════════════════════════════════════════════════════════════
    # VALIDATORS
    # ══════════════════════════════════════════════════════════════

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("LLM_TEMPERATURE must be between 0.0 and 1.0")
        return v

    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        # Overlap must be less than chunk size
        chunk_size = info.data.get("CHUNK_SIZE", 512)
        if v >= chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({v}) must be less than CHUNK_SIZE ({chunk_size})"
            )
        return v


# ── Singleton instance ─────────────────────────────────────────────
# Import this everywhere — one object, loaded once at startup
settings = IcarusSettings()