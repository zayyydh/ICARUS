"""
ICARUS LLM Base
================
Abstract interface every LLM provider must implement.
The Brain never imports Gemini or Claude directly —
it only talks to this interface.

This means swapping providers = one line in .env.
Nothing else changes.

Usage:
    from app.llm.manager import llm
    response = await llm.chat("Bhai kya scene hai?", history=[])
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


# ══════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════

class Role(str, Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


@dataclass
class Message:
    """
    A single message in a conversation.
    Provider-agnostic — every LLM adapter converts this to its own format.
    """
    role:    Role
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """
    Standardised response from any LLM provider.
    The Brain always receives this — never a raw API response.
    """
    content:        str
    model:          str
    provider:       str
    input_tokens:   int  = 0
    output_tokens:  int  = 0
    finish_reason:  str  = "stop"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMConfig:
    """
    Runtime config passed to each LLM call.
    Allows per-request overrides of global settings.
    """
    temperature:  float = 0.7
    max_tokens:   int   = 2048
    system:       str   = ""      # System prompt for this request


# ══════════════════════════════════════════════════════════════════
# ABSTRACT PROVIDER
# ══════════════════════════════════════════════════════════════════

class BaseLLMProvider(ABC):
    """
    Every LLM provider (Gemini, Claude, Ollama) implements this.
    Four methods. That's the entire contract.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name e.g. 'gemini', 'claude', 'ollama'"""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model string e.g. 'gemini-1.5-flash', 'claude-3-5-sonnet'"""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        config:   LLMConfig,
    ) -> LLMResponse:
        """
        Send a conversation and get a response.
        Main method — used for all standard interactions.
        """

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        config:   LLMConfig,
    ) -> AsyncIterator[str]:
        """
        Stream a response token by token.
        Used for long responses — UI shows text appearing live.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify the provider is reachable and the API key works.
        Called on startup and by the /health/ready endpoint.
        """

    # ── Convenience methods (shared by all providers) ─────────────

    def user_message(self, content: str) -> Message:
        return Message(role=Role.USER, content=content)

    def assistant_message(self, content: str) -> Message:
        return Message(role=Role.ASSISTANT, content=content)

    def system_message(self, content: str) -> Message:
        return Message(role=Role.SYSTEM, content=content)