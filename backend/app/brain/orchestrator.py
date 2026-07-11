"""
ICARUS Orchestrator — v2
=========================
Now fully memory-aware.

Every request:
  1. Loads conversation history from short-term memory (Redis)
  2. Loads user facts from long-term memory (SQLite)
  3. Searches vector memory for relevant past context
  4. Routes intent → tool or LLM
  5. Saves the exchange back to all memory layers
"""

import logging
import random
from dataclasses import dataclass, field

from app.brain.intent_router import router as intent_router, RouteResult
from app.config.constants import INTENT, TOOL, THINKING_SOUNDS, LANGUAGE
from app.config.settings import settings
from app.llm.manager import llm
from app.llm.base import Message, Role, LLMConfig
from app.memory.short_term import short_term_memory
from app.memory.long_term import long_term_memory
from app.memory.vector_store import vector_store

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR RESPONSE
# ══════════════════════════════════════════════════════════════════

@dataclass
class OrchestratorResponse:
    text:           str
    intent:         str
    used_llm:       bool            = False
    used_tool:      str | None      = None
    tool_output:    dict | None     = None
    thinking_sound: str             = ""
    tokens_used:    int             = 0
    personality:    str             = "bro"
    language:       str             = "hinglish"
    session_id:     str             = ""


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

class Orchestrator:

    def __init__(self):
        logger.info("Orchestrator initialized")

    # ── Main entry point ──────────────────────────────────────────

    async def handle(
        self,
        text:        str,
        language:    str  = "hinglish",
        personality: str  = "bro",
        history:     list[dict] | None = None,
        session_id:  str  = "",
    ) -> OrchestratorResponse:
        """
        Handle any user input end-to-end.
        Now memory-aware — loads and saves across all three layers.
        """
        history    = history or []
        session_id = session_id or self._new_session_id()

        logger.info(
            "Orchestrator handling request",
            extra={
                "text":        text[:60],
                "language":    language,
                "personality": personality,
                "session_id":  session_id,
            }
        )

        # ── Step 1: Load short-term history from Redis ─────────────
        # If caller passed history, use it. Otherwise load from Redis.
        if not history:
            history = await short_term_memory.get(session_id)

        # ── Step 2: Load user facts from long-term memory ──────────
        memory_context = await long_term_memory.build_memory_context()

        # ── Step 3: Check if this is a memory save/recall command ──
        route = await intent_router.route(text)

        if route.intent == INTENT.MEMORY_SAVE:
            return await self._handle_memory_save(
                text, route, language, personality,
                session_id, memory_context
            )

        if route.intent == INTENT.MEMORY_RECALL:
            return await self._handle_memory_recall(
                text, route, language, personality,
                session_id, memory_context
            )

        # ── Step 4: Search vector memory for relevant past context ──
        vector_context = await vector_store.recall_relevant(text)

        # ── Step 5: Pick thinking sound ────────────────────────────
        thinking_sound = self._pick_thinking_sound(language)

        # ── Step 6: Route to handler ───────────────────────────────
        try:
            if route.intent == INTENT.PERSONALITY_SWITCH:
                response = await self._handle_personality_switch(
                    route, language, thinking_sound
                )

            elif route.intent == INTENT.ICARUS_STATUS:
                response = await self._handle_status(
                    route, language, personality,
                    thinking_sound, memory_context
                )

            elif route.intent == INTENT.ICARUS_HELP:
                response = await self._handle_help(
                    route, language, personality, thinking_sound
                )

            elif route.is_direct_tool:
                response = await self._handle_tool(
                    route, language, personality, thinking_sound
                )

            else:
                response = await self._handle_llm(
                    text, route, language, personality,
                    history, thinking_sound,
                    memory_context, vector_context
                )

            response.session_id = session_id

        except Exception as e:
            logger.error(
                "Orchestrator error",
                extra={"error": str(e), "intent": route.intent.value}
            )
            response = self._error_response(
                e, route.intent.value, language,
                personality, thinking_sound, session_id
            )

        # ── Step 7: Save exchange to memory ───────────────────────
        await self._save_to_memory(
            session_id=session_id,
            user_text=text,
            icarus_text=response.text,
            intent=route.intent.value,
        )

        return response

    # ── Memory handlers ───────────────────────────────────────────

    async def _handle_memory_save(
        self,
        text:           str,
        route:          RouteResult,
        language:       str,
        personality:    str,
        session_id:     str,
        memory_context: str,
    ) -> OrchestratorResponse:
        """Extract and save a fact from user input."""

        # Ask LLM to extract the key fact
        extract_prompt = (
            f"The user said: '{text}'\n"
            f"They want you to remember something. "
            f"Extract: (1) a short snake_case key, (2) the value to remember.\n"
            f"Reply in JSON only: {{\"key\": \"...\", \"value\": \"...\"}}"
        )
        raw = await llm.quick(extract_prompt)

        try:
            import json
            # Strip markdown fences if present
            clean = raw.strip().strip("```json").strip("```").strip()
            parsed = json.loads(clean)
            key   = parsed.get("key", "user_note")
            value = parsed.get("value", text)
        except Exception:
            key   = "user_note"
            value = text

        await long_term_memory.save(key, value, category="user_fact")

        confirmations = {
            "hinglish": f"Yaad kar liya — {value}",
            "hi":       f"Yaad aa gaya — {value}",
            "en":       f"Got it, I'll remember — {value}",
            "mr":       f"Lakshat thevle — {value}",
        }
        reply = confirmations.get(language, confirmations["hinglish"])

        return OrchestratorResponse(
            text=reply,
            intent=route.intent.value,
            used_llm=True,
            personality=personality,
            language=language,
        )

    async def _handle_memory_recall(
        self,
        text:           str,
        route:          RouteResult,
        language:       str,
        personality:    str,
        session_id:     str,
        memory_context: str,
    ) -> OrchestratorResponse:
        """Search memory and answer a recall question."""
        # Search both long-term and vector memory
        lt_context = await long_term_memory.build_memory_context()
        vt_context = await vector_store.recall_relevant(text)

        combined = "\n\n".join(filter(None, [lt_context, vt_context]))

        prompt_msg = (
            f"The user is asking you to recall something: '{text}'\n\n"
            f"Here is what you know:\n{combined}\n\n"
            f"Answer based on this. If you don't know, say so honestly."
        )

        messages = [Message(role=Role.USER, content=prompt_msg)]
        response = await llm.chat(
            messages=messages,
            personality=personality,
            language=language,
        )

        return OrchestratorResponse(
            text=response.content,
            intent=route.intent.value,
            used_llm=True,
            tokens_used=response.total_tokens,
            personality=personality,
            language=language,
        )

    # ── Core handlers ─────────────────────────────────────────────

    async def _handle_tool(
        self,
        route:          RouteResult,
        language:       str,
        personality:    str,
        thinking_sound: str,
    ) -> OrchestratorResponse:
        tool_name   = route.tool.value if route.tool else "unknown"
        tool_result = await self._execute_tool(route)

        if tool_result.get("success"):
            text = self._tool_success_message(route.intent, route.params, language)
        else:
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
        memory_context: str,
        vector_context: str,
    ) -> OrchestratorResponse:
        """LLM response with full memory context injected."""

        # Build message list
        messages: list[Message] = []

        # Inject memory as system context
        context_parts = []
        if memory_context:
            context_parts.append(memory_context)
        if vector_context:
            context_parts.append(vector_context)

        if context_parts:
            messages.append(Message(
                role=Role.SYSTEM,
                content="\n\n".join(context_parts)
            ))

        # Add conversation history
        for h in history[-settings.MAX_HISTORY_TURNS * 2:]:
            role = Role.USER if h.get("role") == "user" else Role.ASSISTANT
            messages.append(Message(role=role, content=h.get("content", "")))

        # Add current message
        messages.append(Message(role=Role.USER, content=text))

        # Tool-assisted LLM (e.g. web search)
        tool_output = None
        tool_name   = None
        if route.tool and route.use_llm:
            tool_result = await self._execute_tool(route)
            if tool_result.get("success") and tool_result.get("output"):
                tool_name   = route.tool.value
                tool_output = tool_result
                messages.append(Message(
                    role=Role.SYSTEM,
                    content=(
                        f"[Tool result — {tool_name}]:\n"
                        f"{tool_result['output']}\n\n"
                        "Use this to answer the user."
                    )
                ))

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
        profile = route.params.get("profile", "bro")
        confirmations = {
            "en":       f"Switching to {profile} mode.",
            "hi":       f"{profile} mode activate ho gaya.",
            "hinglish": f"Theek hai, {profile} mode mein aa gaya.",
            "mr":       f"{profile} mode switch kela.",
            "ur":       f"{profile} mode mein aa gaya hoon.",
        }
        return OrchestratorResponse(
            text=confirmations.get(language, confirmations["hinglish"]),
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
        memory_context: str,
    ) -> OrchestratorResponse:
        messages = []
        if memory_context:
            messages.append(Message(role=Role.SYSTEM, content=memory_context))
        messages.append(Message(
            role=Role.USER,
            content="How are you doing? Give a short in-character response."
        ))
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
        prompt = (
            "List your key capabilities briefly — music, GitHub, "
            "web search, code, browser automation, memory, RAG, "
            "personality switching. Keep it punchy and in-character."
        )
        messages = [Message(role=Role.USER, content=prompt)]
        response = await llm.chat(
            messages=messages, personality=personality, language=language
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

    # ── Memory persistence ────────────────────────────────────────

    async def _save_to_memory(
        self,
        session_id:  str,
        user_text:   str,
        icarus_text: str,
        intent:      str,
    ) -> None:
        """Save the completed exchange to all memory layers."""
        try:
            # Short-term — Redis
            await short_term_memory.add(session_id, "user",      user_text)
            await short_term_memory.add(session_id, "assistant", icarus_text)

            # Vector — only for substantive conversations
            if intent in ("conversation", "question", "research", "explain"):
                await vector_store.store_conversation_turn(
                    session_id=session_id,
                    user_msg=user_text,
                    icarus_msg=icarus_text,
                )
        except Exception as e:
            logger.warning(
                "Memory save failed — continuing without saving",
                extra={"error": str(e)}
            )

    # ── Tool execution ────────────────────────────────────────────

    async def _execute_tool(self, route: RouteResult) -> dict:
        """Stub implementations — real tools wired in Phase 4."""
        intent = route.intent
        params = route.params

        if intent == INTENT.MUSIC_PLAY:
            return {"success": True, "output": f"Playing '{params.get('query', '')}'"}
        if intent == INTENT.MUSIC_PAUSE:
            return {"success": True, "output": "Music paused"}
        if intent == INTENT.MUSIC_STOP:
            return {"success": True, "output": "Music stopped"}
        if intent == INTENT.MUSIC_NEXT:
            return {"success": True, "output": "Skipped to next"}
        if intent == INTENT.GITHUB_CREATE:
            name = params.get("repo_name", "new-repo")
            return {
                "success": True,
                "output":  f"Repository '{name}' created",
                "url":     f"https://github.com/{settings.GITHUB_USERNAME}/{name}",
            }
        if intent == INTENT.GITHUB_PUSH:
            return {"success": True, "output": "Code pushed to GitHub"}
        if intent == INTENT.GITHUB_LIST:
            return {"success": True, "output": "Fetching your repositories..."}
        if intent == INTENT.WEB_SEARCH:
            return {
                "success": True,
                "output": f"[Search results for '{params.get('query', '')}']",
            }
        if intent == INTENT.BROWSER_OPEN:
            return {"success": True, "output": f"Opening '{params.get('target', '')}'"}
        if intent == INTENT.CODE_RUN:
            return {"success": True, "output": "Code executor coming in Phase 4"}

        return {"success": False, "error": f"No tool for {intent}"}

    # ── Helpers ───────────────────────────────────────────────────

    def _pick_thinking_sound(self, language: str) -> str:
        try:
            lang_enum = LANGUAGE(language)
        except ValueError:
            lang_enum = LANGUAGE.HINGLISH
        sounds = THINKING_SOUNDS.get(lang_enum, ["..."])
        return random.choice(sounds)

    def _tool_success_message(self, intent, params, language) -> str:
        query  = params.get("query", "")
        target = params.get("target", "")
        repo   = params.get("repo_name", "")
        msgs = {
            INTENT.MUSIC_PLAY:  {"hinglish": f"Haan, '{query}' laga raha hoon.", "en": f"Playing '{query}'."},
            INTENT.MUSIC_PAUSE: {"hinglish": "Music pause kar diya.", "en": "Music paused."},
            INTENT.MUSIC_STOP:  {"hinglish": "Music band kar diya.", "en": "Music stopped."},
            INTENT.MUSIC_NEXT:  {"hinglish": "Agla track.", "en": "Next track."},
            INTENT.BROWSER_OPEN:{"hinglish": f"'{target}' khol raha hoon.", "en": f"Opening '{target}'."},
            INTENT.GITHUB_CREATE:{"hinglish": f"Repo '{repo}' ban gaya bhai.", "en": f"Repo '{repo}' created."},
            INTENT.GITHUB_PUSH: {"hinglish": "Code GitHub pe push ho gaya.", "en": "Code pushed."},
        }
        intent_msgs = msgs.get(intent, {})
        return intent_msgs.get(language, intent_msgs.get("hinglish", "Done."))

    async def _llm_error_explanation(self, route, error, language, personality) -> str:
        prompt = (
            f"A tool failed. Intent: {route.intent.value}. "
            f"Error: {error}. Explain briefly and helpfully."
        )
        return await llm.quick(prompt, system=f"Language: {language}")

    def _error_response(self, error, intent, language, personality, thinking_sound, session_id) -> OrchestratorResponse:
        msgs = {
            "hinglish": "Bhai kuch gadbad ho gayi. Dobara try karo.",
            "hi":       "Kuch galat ho gaya. Phir koshish karo.",
            "en":       "Something went wrong. Please try again.",
            "mr":       "Kahi chuk zali. Parat try kara.",
        }
        logger.error("Orchestrator fallback", extra={"error": str(error)})
        return OrchestratorResponse(
            text=messages.get(language, msgs["hinglish"]),
            intent=intent,
            used_llm=False,
            thinking_sound=thinking_sound,
            personality=personality,
            language=language,
            session_id=session_id,
        )

    def _new_session_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]


# ── Singleton ──────────────────────────────────────────────────────
orchestrator = Orchestrator()