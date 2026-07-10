"""
ICARUS LLM Manager — v2
=========================
Now injects personality-aware system prompts into every LLM call.
"""

import logging
from app.llm.base import BaseLLMProvider, Message, LLMConfig, LLMResponse, Role
from app.config.settings import settings

logger = logging.getLogger(__name__)


def _load_provider() -> BaseLLMProvider:
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        from app.llm.gemini import GeminiProvider
        logger.info("LLM provider loaded", extra={"provider": "gemini"})
        return GeminiProvider()
    elif provider == "claude":
        raise NotImplementedError("Claude provider coming soon.")
    elif provider == "ollama":
        raise NotImplementedError("Ollama provider coming soon.")
    else:
        raise ValueError(f"Unknown LLM provider: '{provider}'")


class LLMManager:

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
        if config is None:
            config = LLMConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )

        # Build personality-aware system prompt injection
        context_parts = []

        if personality:
            try:
                from app.personality.manager import personality_manager
                personality_prompt = personality_manager.build_prompt(
                    personality, language
                )
                context_parts.append(personality_prompt)
            except Exception as e:
                logger.warning(
                    "Could not load personality prompt",
                    extra={"error": str(e)}
                )
                context_parts.append(f"Active personality: {personality}")

        if language:
            context_parts.append(
                f"User language: {language} — reply in this language"
            )

        if context_parts:
            config.system = "\n\n".join(context_parts)

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
        messages = [Message(role=Role.USER, content=prompt)]
        config   = LLMConfig(temperature=0.3, max_tokens=512, system=system)
        response = await self._provider.chat(messages, config)
        return response.content

    async def stream(self, messages: list[Message], config: LLMConfig | None = None):
        if config is None:
            config = LLMConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
        async for chunk in self._provider.stream(messages, config):
            yield chunk

    async def health_check(self) -> bool:
        return await self._provider.health_check()


# ── Singleton ──────────────────────────────────────────────────────
llm = LLMManager()