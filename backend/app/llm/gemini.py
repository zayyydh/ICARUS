"""
ICARUS Gemini Provider — v2
============================
Updated to use google.genai (new SDK).
google.generativeai is deprecated and will stop receiving updates.

Install the new SDK:
    pip install google-genai
"""

import asyncio
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.llm.base import (
    BaseLLMProvider,
    Message,
    LLMConfig,
    LLMResponse,
    Role,
)
from app.config.settings import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# ICARUS SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════

ICARUS_SYSTEM_PROMPT = """You are ICARUS — Intelligent Conversational Agent with Reasoning, Understanding & Synthesis.
You are a personal AI Operating System, not a chatbot.

IDENTITY:
- You are ICARUS. Never say "As an AI..." — you are ICARUS.
- You were built by Zayd as his personal AI Operating System.
- You are calm, capable, precise — but never robotic or cold.
- You have a subtle wit. Intelligent but never sarcastic unless the user is.
- You anticipate what the user needs, not just what they literally asked.
- You are honest about uncertainty. You never fabricate facts.

LANGUAGE INTELLIGENCE:
You are fluent in Hindi, Marathi, Urdu, Hinglish, and English.

CRITICAL RULE: Always reply in the SAME language the user used.
- User speaks Hinglish → reply in Hinglish
- User speaks Hindi → reply in Hindi
- User speaks English → reply in English
- User mixes languages mid-sentence → you mix too

Hinglish example (correct):
  User: "bhai ye search kar de"
  You:  "Haan bhai, abhi karta hoon."
  NOT:  "Of course, I will search for that now."

INDIAN CULTURAL CONTEXT:
- You understand Indian slang: yaar, bhai, arre, pakka, jugaad, mast,
  bindaas, jhakas, lafda, setting, timepass, bakwaas, ghanta, etc.
- You know Indian cities, festivals, cricket, Bollywood, geography.
- "kal" = tomorrow OR yesterday depending on tense.
- "bas" = stop OR just/enough depending on context.
- "accha" = okay / I see / really — you read the tone.

BEHAVIOR:
- Be concise unless depth is explicitly needed.
- When you complete an action, confirm it briefly in the user's language.
- Never translate the user's words back to them unnecessarily.
- When you don't know something, say so directly.
- You remember context from earlier in the conversation naturally."""


# ══════════════════════════════════════════════════════════════════
# GEMINI PROVIDER
# ══════════════════════════════════════════════════════════════════

class GeminiProvider(BaseLLMProvider):

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(self):
        # New SDK — initialise client with API key
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_MODEL
        logger.info(
            "Gemini provider initialized",
            extra={"model": self._model_name}
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model_name

    # ── Convert our Message format → new SDK format ───────────────
    def _build_contents(self, messages: list[Message]) -> list[types.Content]:
        """
        Converts our Message list to google.genai Content objects.
        Skips system messages — those go in the config separately.
        Maps Role.ASSISTANT → 'model' (Gemini's term for assistant).
        """
        contents = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue   # System prompt handled separately
            gemini_role = "model" if msg.role == Role.ASSISTANT else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=msg.content)],
                )
            )
        return contents

    def _build_config(self, config: LLMConfig) -> types.GenerateContentConfig:
        """Build the generation config for new SDK."""
        system = ICARUS_SYSTEM_PROMPT
        if config.system:
            system = f"{system}\n\nACTIVE CONTEXT:\n{config.system}"

        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )

    # ── Main chat method ──────────────────────────────────────────
    async def chat(
        self,
        messages: list[Message],
        config:   LLMConfig,
    ) -> LLMResponse:
        """
        Send conversation to Gemini, get a full response.
        Uses new google.genai SDK.
        """
        contents = self._build_contents(messages)
        gen_config = self._build_config(config)

        for attempt in range(self.MAX_RETRIES):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=self._model_name,
                        contents=contents,
                        config=gen_config,
                    )
                )

                content = response.text

                # Token usage
                input_tokens  = 0
                output_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens  = getattr(response.usage_metadata, "prompt_token_count",      0) or 0
                    output_tokens = getattr(response.usage_metadata, "candidates_token_count",  0) or 0

                logger.debug(
                    "Gemini response received",
                    extra={
                        "tokens_in":  input_tokens,
                        "tokens_out": output_tokens,
                        "attempt":    attempt + 1,
                    }
                )

                return LLMResponse(
                    content=content,
                    model=self._model_name,
                    provider=self.name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            except Exception as e:
                logger.warning(
                    f"Gemini error on attempt {attempt + 1}",
                    extra={"error": str(e)}
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(
                        "Gemini chat failed after all retries",
                        extra={"error": str(e)}
                    )
                    raise

    # ── Streaming ─────────────────────────────────────────────────
    async def stream(
        self,
        messages: list[Message],
        config:   LLMConfig,
    ) -> AsyncIterator[str]:
        """Stream response token by token using new SDK."""
        contents   = self._build_contents(messages)
        gen_config = self._build_config(config)

        loop = asyncio.get_event_loop()
        response_stream = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content_stream(
                model=self._model_name,
                contents=contents,
                config=gen_config,
            )
        )

        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    # ── Health check ──────────────────────────────────────────────
    async def health_check(self) -> bool:
        """
        Verify Gemini is reachable and the API key is valid.
        Uses a neutral prompt that won't trigger safety filters.
        """
        try:
            test_messages = [
                Message(role=Role.USER, content="Say hello in one word.")
            ]
            config = LLMConfig(temperature=0.0, max_tokens=20)
            response = await self.chat(test_messages, config)
            return bool(response.content)
        except Exception as e:
            logger.error(
                "Gemini health check failed",
                extra={"error": str(e)}
            )
            return False