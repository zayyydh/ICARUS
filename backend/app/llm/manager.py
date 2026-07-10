"""
ICARUS LLM Manager
===================
The single entry point for all LLM interactions.
Every module imports THIS — never a provider directly.

Reads LLM_PROVIDER from .env and returns the right provider.
Swapping models = one line in .env. Zero code changes.

Usage anywhere in ICARUS:
    from app.llm.manager import llm
    response = await llm.chat(messages, config)
"""

import logging

from app.llm.base import BaseLLMProvider, Message, LLMConfig, LLMResponse, Role
from app.config.settings import settings

logger = logging.getLogger(__name__)


def _load_provider() -> BaseLLMProvider:
    """
    Reads LLM_PROVIDER from settings and instantiates
    the correct provider. Called once at startup.
    """
    provider = settings.LLM_PROVIDER

    if provider == "gemini":
        from app.llm.gemini import GeminiProvider
        logger.info("LLM provider loaded", extra={"provider": "gemini"})
        return GeminiProvider()

    elif provider == "claude":
        raise NotImplementedError(
            "Claude provider not yet implemented. "
            "Set LLM_PROVIDER=gemini in .env"
        )

    elif provider == "ollama":
        raise NotImplementedError(
            "Ollama provider not yet implemented. "
            "Set LLM_PROVIDER=gemini in .env"
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Valid options: gemini, claude, ollama"
        )


class LLMManager:
    """
    Thin wrapper around the active provider.
    Adds logging, error handling, and convenience methods
    on top of the raw provider interface.

    This is what the Brain, Tools, and RAG engine all use.
    """

    def __init__(self):
        self._provider = _load_provider()
        logger.info(
            "LLM Manager ready",
            extra={
                "provider": self._provider.name,
                "model":    self._provider.model,
            }
        )

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model_name(self) -> str:
        return self._provider.model

    async def chat(
        self,
        messages:    list[Message],
        config:      LLMConfig | None = None,
        personality: str = "",
        language:    str = "",
    ) -> LLMResponse:
        """
        Main method for all ICARUS LLM calls.

        Args:
            messages:    Conversation history + current message
            config:      Optional per-request LLM settings
            personality: Active personality name — injected into system prompt
            language:    Detected language — injected into system prompt

        Returns:
            LLMResponse with content, token counts, provider info
        """
        if config is None:
            config = LLMConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )

        # Inject personality and language context into system prompt
        context_parts = []
        if personality:
            context_parts.append(f"Active personality: {personality}")
        if language:
            context_parts.append(
                f"User's language: {language} — reply in this language"
            )

        if context_parts:
            config.system = "\n".join(context_parts)

        logger.debug(
            "LLM chat request",
            extra={
                "messages":    len(messages),
                "personality": personality,
                "language":    language,
            }
        )

        response = await self._provider.chat(messages, config)

        logger.debug(
            "LLM chat response",
            extra={
                "tokens": response.total_tokens,
                "chars":  len(response.content),
            }
        )

        return response

    async def quick(self, prompt: str, system: str = "") -> str:
        """
        One-shot prompt → response string.
        For simple internal tasks that don't need history.

        Usage:
            text = await llm.quick("Summarize this in 2 sentences: ...")
        """
        messages = [Message(role=Role.USER, content=prompt)]
        config   = LLMConfig(
            temperature=0.3,
            max_tokens=512,
            system=system,
        )
        response = await self._provider.chat(messages, config)
        return response.content

    async def stream(
        self,
        messages: list[Message],
        config:   LLMConfig | None = None,
    ):
        """Streaming passthrough to active provider."""
        if config is None:
            config = LLMConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
        async for chunk in self._provider.stream(messages, config):
            yield chunk

    async def health_check(self) -> bool:
        """Check if the active LLM provider is reachable."""
        return await self._provider.health_check()


# ── Singleton ──────────────────────────────────────────────────────
# Import this everywhere. One instance, loaded once.
# All modules share the same provider connection.
llm = LLMManager()
