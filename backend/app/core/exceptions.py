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
