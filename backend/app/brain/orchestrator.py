"""
ICARUS Orchestrator
====================
The central coordinator of ICARUS.

Receives a RouteResult from the Intent Router and decides:
  - Which tools to call
  - Whether to use the LLM
  - How to build the final prompt
  - What to return to the user

The Orchestrator is the only module that knows about everything.
Every other module knows only about its own domain.

Flow:
  User input
      │
  Intent Router    → RouteResult
      │
  Orchestrator     → coordinates tools + LLM + memory + personality
      │
  Final response   → text back to user

Usage:
    from app.brain.orchestrator import orchestrator
    response = await orchestrator.handle(
        text="gana baja Kesariya",
        language="hinglish",
        personality="bro",
        history=[],
    )
"""

import logging
from dataclasses import dataclass, field

from app.brain.intent_router import router as intent_router, RouteResult
from app.config.constants import INTENT, TOOL, THINKING_SOUNDS, LANGUAGE
from app.config.settings import settings
from app.llm.manager import llm
from app.llm.base import Message, Role, LLMConfig

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR RESPONSE
# ══════════════════════════════════════════════════════════════════

@dataclass
class OrchestratorResponse:
    """
    Everything the API layer needs to respond to the user.

    text:           The final reply text
    intent:         What ICARUS understood the user wanted
    used_llm:       Whether Gemini was involved
    used_tool:      Which tool was called (if any)
    tool_output:    Raw tool result (for debugging)
    thinking_sound: Short sound to play while processing (voice UX)
    tokens_used:    LLM tokens consumed (0 if no LLM call)
    personality:    Active personality that shaped the response
    language:       Language the response is in
    """
    text:           str
    intent:         str
    used_llm:       bool               = False
    used_tool:      str | None         = None
    tool_output:    dict | None        = None
    thinking_sound: str                = ""
    tokens_used:    int                = 0
    personality:    str                = "bro"
    language:       str                = "hinglish"


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

class Orchestrator:
    """
    Coordinates the full ICARUS response pipeline.

    Design principles:
    1. Try tools first — LLM is last resort, not first instinct
    2. Every path returns an OrchestratorResponse — no exceptions escape
    3. Personality and language are injected at the LLM layer
    4. Tool failures degrade gracefully — ICARUS explains what went wrong
    """

    def __init__(self):
        logger.info("Orchestrator initialized")

    # ── Main entry point ──────────────────────────────────────────

    async def handle(
        self,
        text:        str,
        language:    str = "hinglish",
        personality: str = "bro",
        history:     list[dict] | None = None,
    ) -> OrchestratorResponse:
        """
        Handle any user input end-to-end.
        This is the single method the API layer calls.
        """
        history = history or []

        logger.info(
            "Orchestrator handling request",
            extra={
                "text":        text[:60],
                "language":    language,
                "personality": personality,
            }
        )

        # Step 1 — Route the intent
        route = await intent_router.route(text)

        logger.info(
            "Intent routed",
            extra={
                "intent":     route.intent.value,
                "use_llm":    route.use_llm,
                "tool":       route.tool.value if route.tool else None,
                "confidence": route.confidence,
            }
        )

        # Step 2 — Pick thinking sound for voice UX
        thinking_sound = self._pick_thinking_sound(language)

        # Step 3 — Route to appropriate handler
        try:
            if route.intent == INTENT.PERSONALITY_SWITCH:
                return await self._handle_personality_switch(
                    route, language, thinking_sound
                )

            if route.intent == INTENT.ICARUS_STATUS:
                return await self._handle_status(
                    route, language, personality, thinking_sound
                )

            if route.intent == INTENT.ICARUS_HELP:
                return await self._handle_help(
                    route, language, personality, thinking_sound
                )

            if route.is_direct_tool:
                return await self._handle_tool(
                    route, language, personality, thinking_sound
                )

            # Default — LLM handles it
            return await self._handle_llm(
                text, route, language, personality,
                history, thinking_sound
            )

        except Exception as e:
            logger.error(
                "Orchestrator error",
                extra={"error": str(e), "intent": route.intent.value}
            )
            return self._error_response(
                e, route.intent.value, language, personality, thinking_sound
            )

    # ── Handlers ──────────────────────────────────────────────────

    async def _handle_tool(
        self,
        route:          RouteResult,
        language:       str,
        personality:    str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """
        Direct tool execution — no LLM involved.
        Fast path for deterministic actions like playing music.
        """
        tool_name = route.tool.value if route.tool else "unknown"
        logger.info(
            "Executing tool directly",
            extra={"tool": tool_name, "params": route.params}
        )

        # Tool registry lookup — Phase 4 will wire real tools here
        # For now, return a structured stub so the pipeline works end-to-end
        tool_result = await self._execute_tool(route)

        if tool_result.get("success"):
            # Tool succeeded — confirm in user's language without LLM
            text = self._tool_success_message(
                route.intent, route.params, language
            )
        else:
            # Tool failed — LLM generates a helpful error message
            text = await self._llm_error_explanation(
                route, tool_result.get("error", ""), language, personality
            )

        return OrchestratorResponse(
            text=text,
            intent=route.intent.value,
            used_llm=False,
            used_tool=tool_name,
            tool_output=tool_result,
            thinking_sound=thinking_sound,
            personality=personality,
            language=language,
        )

    async def _handle_llm(
        self,
        text:           str,
        route:          RouteResult,
        language:       str,
        personality:    str,
        history:        list[dict],
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """
        LLM-powered response.
        Used for conversation, research, writing, code explanation etc.
        """
        # Build message list from history
        messages: list[Message] = []
        for h in history:
            role = Role.USER if h.get("role") == "user" else Role.ASSISTANT
            messages.append(Message(role=role, content=h.get("content", "")))

        # Add context about the detected intent to help LLM respond better
        enriched_text = self._enrich_with_intent_context(text, route)
        messages.append(Message(role=Role.USER, content=enriched_text))

        # If tool was also needed (e.g. web search), run it first
        tool_output = None
        tool_name   = None
        if route.tool and route.use_llm:
            tool_result = await self._execute_tool(route)
            if tool_result.get("success") and tool_result.get("output"):
                tool_name   = route.tool.value
                tool_output = tool_result
                # Inject tool results into context
                context_msg = (
                    f"[Tool result from {tool_name}]:\n"
                    f"{tool_result['output']}\n\n"
                    f"Use this information to answer the user's question."
                )
                messages.append(
                    Message(role=Role.SYSTEM, content=context_msg)
                )

        response = await llm.chat(
            messages=messages,
            personality=personality,
            language=language,
        )

        return OrchestratorResponse(
            text=response.content,
            intent=route.intent.value,
            used_llm=True,
            used_tool=tool_name,
            tool_output=tool_output,
            thinking_sound=thinking_sound,
            tokens_used=response.total_tokens,
            personality=personality,
            language=language,
        )

    async def _handle_personality_switch(
        self,
        route:          RouteResult,
        language:       str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """Handle personality switch without LLM."""
        profile = route.params.get("profile", "bro")

        confirmations = {
            "en":       f"Switching to {profile} mode.",
            "hi":       f"{profile} mode activate ho gaya.",
            "hinglish": f"Theek hai, {profile} mode mein aa gaya.",
            "mr":       f"{profile} mode switch kela.",
            "ur":       f"{profile} mode mein aa gaya hoon.",
        }
        text = confirmations.get(language, confirmations["hinglish"])

        return OrchestratorResponse(
            text=text,
            intent=route.intent.value,
            used_llm=False,
            thinking_sound=thinking_sound,
            personality=profile,
            language=language,
        )

    async def _handle_status(
        self,
        route:          RouteResult,
        language:       str,
        personality:    str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """ICARUS status — quick personality-aware response."""
        messages = [
            Message(
                role=Role.USER,
                content="How are you doing? Give a short, in-character response."
            )
        ]
        response = await llm.chat(
            messages=messages,
            personality=personality,
            language=language,
        )
        return OrchestratorResponse(
            text=response.content,
            intent=route.intent.value,
            used_llm=True,
            thinking_sound=thinking_sound,
            tokens_used=response.total_tokens,
            personality=personality,
            language=language,
        )

    async def _handle_help(
        self,
        route:          RouteResult,
        language:       str,
        personality:    str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """List ICARUS capabilities in the user's language."""
        prompt = (
            "List your key capabilities briefly. "
            "Music, GitHub, web search, code, browser automation, "
            "memory, RAG knowledge base, personality switching. "
            "Keep it punchy and in-character."
        )
        messages = [Message(role=Role.USER, content=prompt)]
        response = await llm.chat(
            messages=messages,
            personality=personality,
            language=language,
        )
        return OrchestratorResponse(
            text=response.content,
            intent=route.intent.value,
            used_llm=True,
            thinking_sound=thinking_sound,
            tokens_used=response.total_tokens,
            personality=personality,
            language=language,
        )

    # ── Tool execution ────────────────────────────────────────────

    async def _execute_tool(self, route: RouteResult) -> dict:
        """
        Execute a tool by name.
        Phase 4 will wire real tool implementations here via the registry.
        For now returns structured stubs so the pipeline works end-to-end.
        """
        intent = route.intent
        params = route.params

        # ── Music stubs ───────────────────────────────────────────
        if intent == INTENT.MUSIC_PLAY:
            query = params.get("query", "")
            return {
                "success": True,
                "output":  f"Playing '{query}' on YouTube",
                "query":   query,
            }

        if intent == INTENT.MUSIC_PAUSE:
            return {"success": True, "output": "Music paused"}

        if intent == INTENT.MUSIC_STOP:
            return {"success": True, "output": "Music stopped"}

        if intent == INTENT.MUSIC_NEXT:
            return {"success": True, "output": "Skipped to next track"}

        # ── GitHub stubs ──────────────────────────────────────────
        if intent == INTENT.GITHUB_CREATE:
            name = params.get("repo_name", "new-repo")
            return {
                "success": True,
                "output":  f"Repository '{name}' created",
                "url":     f"https://github.com/{settings.GITHUB_USERNAME}/{name}",
            }

        if intent == INTENT.GITHUB_PUSH:
            return {
                "success": True,
                "output":  "Code pushed to GitHub successfully",
            }

        if intent == INTENT.GITHUB_LIST:
            return {
                "success": True,
                "output":  "Fetching your repositories...",
            }

        # ── Web search stub ───────────────────────────────────────
        if intent == INTENT.WEB_SEARCH:
            query = params.get("query", "")
            return {
                "success": True,
                "output":  f"[Web search results for '{query}' will appear here]",
                "query":   query,
            }

        # ── Browser stub ──────────────────────────────────────────
        if intent == INTENT.BROWSER_OPEN:
            target = params.get("target", "")
            return {
                "success": True,
                "output":  f"Opening '{target}'",
            }

        # ── Code stub ─────────────────────────────────────────────
        if intent == INTENT.CODE_RUN:
            return {
                "success": True,
                "output":  "Code execution ready — tool coming in Phase 4",
            }

        return {"success": False, "error": f"No tool implemented for {intent}"}

    # ── Helpers ───────────────────────────────────────────────────

    def _enrich_with_intent_context(
        self, text: str, route: RouteResult
    ) -> str:
        """
        Adds intent context to the user message.
        Helps LLM give more relevant responses.
        """
        if route.intent == INTENT.CONVERSATION:
            return text
        return f"{text}\n[Detected intent: {route.intent.value}]"

    def _pick_thinking_sound(self, language: str) -> str:
        """Pick a random thinking sound in the right language."""
        import random
        try:
            lang_enum = LANGUAGE(language)
        except ValueError:
            lang_enum = LANGUAGE.HINGLISH
        sounds = THINKING_SOUNDS.get(lang_enum, ["..."])
        return random.choice(sounds)

    def _tool_success_message(
        self,
        intent:   INTENT,
        params:   dict,
        language: str,
    ) -> str:
        """
        Short confirmation message after a successful direct tool call.
        No LLM needed — just a canned response in the right language.
        """
        query = params.get("query", "")
        target = params.get("target", "")
        repo   = params.get("repo_name", "")

        messages = {
            INTENT.MUSIC_PLAY: {
                "hinglish": f"Haan, '{query}' laga raha hoon.",
                "hi":       f"'{query}' chala raha hoon.",
                "en":       f"Playing '{query}'.",
                "mr":       f"'{query}' lavto.",
            },
            INTENT.MUSIC_PAUSE: {
                "hinglish": "Music pause kar diya.",
                "hi":       "Music ruk gaya.",
                "en":       "Music paused.",
                "mr":       "Music pause kela.",
            },
            INTENT.MUSIC_STOP: {
                "hinglish": "Music band kar diya.",
                "hi":       "Music band ho gaya.",
                "en":       "Music stopped.",
                "mr":       "Music band kela.",
            },
            INTENT.MUSIC_NEXT: {
                "hinglish": "Agla track laga raha hoon.",
                "hi":       "Agla gaana.",
                "en":       "Next track.",
                "mr":       "Pudcha track.",
            },
            INTENT.BROWSER_OPEN: {
                "hinglish": f"'{target}' khol raha hoon.",
                "hi":       f"'{target}' khul raha hai.",
                "en":       f"Opening '{target}'.",
                "mr":       f"'{target}' ughadto.",
            },
            INTENT.GITHUB_CREATE: {
                "hinglish": f"Repo '{repo}' ban gaya bhai.",
                "hi":       f"Repo '{repo}' ban gaya.",
                "en":       f"Repository '{repo}' created.",
                "mr":       f"Repo '{repo}' tayar.",
            },
            INTENT.GITHUB_PUSH: {
                "hinglish": "Code GitHub pe push ho gaya.",
                "hi":       "Code push ho gaya.",
                "en":       "Code pushed to GitHub.",
                "mr":       "Code push jhala.",
            },
        }

        intent_msgs = messages.get(intent, {})
        return intent_msgs.get(
            language,
            intent_msgs.get("hinglish", "Done.")
        )

    async def _llm_error_explanation(
        self,
        route:      RouteResult,
        error:      str,
        language:   str,
        personality: str,
    ) -> str:
        """When a tool fails, LLM explains what went wrong."""
        prompt = (
            f"A tool failed. Intent was: {route.intent.value}. "
            f"Error: {error}. "
            f"Explain this briefly and helpfully to the user."
        )
        return await llm.quick(prompt, system=f"Language: {language}")

    def _error_response(
        self,
        error:          Exception,
        intent:         str,
        language:       str,
        personality:    str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        """Fallback response when something unexpected goes wrong."""
        messages = {
            "hinglish": "Bhai kuch gadbad ho gayi. Dobara try karo.",
            "hi":       "Kuch galat ho gaya. Phir koshish karo.",
            "en":       "Something went wrong. Please try again.",
            "mr":       "Kahi chuk zali. Parat try kara.",
            "ur":       "Kuch masla hua. Dobara koshish karein.",
        }
        logger.error("Orchestrator fallback error", extra={"error": str(error)})
        return OrchestratorResponse(
            text=messages.get(language, messages["hinglish"]),
            intent=intent,
            used_llm=False,
            thinking_sound=thinking_sound,
            personality=personality,
            language=language,
        )


# ── Singleton ──────────────────────────────────────────────────────
orchestrator = Orchestrator()