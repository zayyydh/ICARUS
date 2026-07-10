"""
ICARUS Intent Router
=====================
Decides what to do with every user input — BEFORE touching the LLM.

Priority order:
  1. Keyword match    → direct tool call (zero LLM cost)
  2. Pattern match    → structured intent with extracted params
  3. LLM fallback     → Gemini classifies ambiguous input
  4. Conversation     → pure chat, goes straight to LLM

This is ADR-003 in action:
  "Why intent routing before the LLM?"
  Because "gana baja Kesariya" doesn't need Gemini to understand.
  Routing it directly saves ~500ms and one API call every time.

Usage:
    from app.brain.intent_router import router
    result = await router.route("gana baja Kesariya")
    # result.intent   == INTENT.MUSIC_PLAY
    # result.params   == {"query": "Kesariya"}
    # result.use_llm  == False
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any

from app.config.constants import (
    INTENT,
    INTENT_TRIGGERS,
    DIRECT_TOOL_INTENTS,
    LLM_ASSISTED_INTENTS,
    TOOL,
)
from app.config.settings import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# ROUTING RESULT
# ══════════════════════════════════════════════════════════════════

@dataclass
class RouteResult:
    """
    Everything the Orchestrator needs to handle a user request.

    intent:     What the user wants to do
    params:     Extracted parameters (song name, repo name, etc.)
    use_llm:    Should Gemini be involved?
    tool:       Which tool to call (if any)
    confidence: How sure we are (0.0 - 1.0)
    raw_input:  Original user text (preserved for LLM if needed)
    """
    intent:     INTENT
    params:     dict[str, Any]     = field(default_factory=dict)
    use_llm:    bool               = True
    tool:       TOOL | None        = None
    confidence: float              = 1.0
    raw_input:  str                = ""

    @property
    def is_direct_tool(self) -> bool:
        """True if this can be handled by a tool with no LLM."""
        return self.tool is not None and not self.use_llm

    @property
    def needs_llm_only(self) -> bool:
        """True if this is pure conversation — no tool needed."""
        return self.use_llm and self.tool is None


# ══════════════════════════════════════════════════════════════════
# PARAMETER EXTRACTORS
# These regex patterns pull structured data from natural language.
# Run BEFORE any LLM call — fast and deterministic.
# ══════════════════════════════════════════════════════════════════

# Music — extract song/artist name after trigger words
_MUSIC_PLAY_PATTERN = re.compile(
    r"(?:play|baja|laga|bajao|chalao|suno|gana|gaana|song|music|track)"
    r"\s+(?:kar[eo]?\s+)?"
    r"(.+)",
    re.IGNORECASE,
)

# GitHub — extract repo name
_GITHUB_CREATE_PATTERN = re.compile(
    r"(?:create|new|naya|banao|banana)\s+(?:repo|repository)\s*"
    r"(?:called|named|ka naam|naam)?\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?",
    re.IGNORECASE,
)

_GITHUB_PUSH_PATTERN = re.compile(
    r"(?:push|upload|commit|deploy)\s+(?:to\s+)?(?:github|git)?"
    r"\s*(?:repo|repository)?\s*['\"]?([a-zA-Z0-9_\-]*)['\"]?",
    re.IGNORECASE,
)

# Browser — extract URL or app name
_BROWSER_OPEN_PATTERN = re.compile(
    r"(?:open|khol|launch|go to|jaao)\s+(.+)",
    re.IGNORECASE,
)

# Web search — extract query
_SEARCH_PATTERN = re.compile(
    r"(?:search|dhundh|find|look up|google|batao)\s+(?:kar[eo]?\s+)?(.+)",
    re.IGNORECASE,
)

# Personality switch — extract profile name
_PERSONALITY_PATTERN = re.compile(
    r"(?:switch to|change to|enable|activate|mode)\s+"
    r"(bro|developer|dev|mentor|coach|night.?owl|minimalist)",
    re.IGNORECASE,
)

# Personality normalisation map
_PERSONALITY_MAP = {
    "dev": "developer",
    "developer": "developer",
    "bro": "bro",
    "mentor": "mentor",
    "coach": "coach",
    "nightowl": "night_owl",
    "night owl": "night_owl",
    "night-owl": "night_owl",
    "minimalist": "minimalist",
}


# ══════════════════════════════════════════════════════════════════
# INTENT ROUTER
# ══════════════════════════════════════════════════════════════════

class IntentRouter:
    """
    Routes user input to the correct handling path.

    Three-stage pipeline:
      Stage 1 — Keyword scan      (O(n) string matching, ~0ms)
      Stage 2 — Regex extraction  (structured param extraction, ~1ms)
      Stage 3 — LLM fallback      (only for ambiguous input)
    """

    def __init__(self):
        # Pre-process trigger map for fast lookup
        # Maps each keyword → its intent
        self._keyword_index: dict[str, INTENT] = {}
        for intent, keywords in INTENT_TRIGGERS.items():
            for kw in keywords:
                self._keyword_index[kw.lower()] = intent
        logger.info(
            "Intent router initialized",
            extra={"keywords": len(self._keyword_index)}
        )

    # ── Public API ────────────────────────────────────────────────

    async def route(self, text: str) -> RouteResult:
        """
        Main routing method. Call this for every user input.
        Returns a RouteResult the Orchestrator acts on.
        """
        text_clean = text.strip()
        text_lower = text_clean.lower()

        logger.debug("Routing input", extra={"text": text_clean[:60]})

        # Stage 1 — keyword scan
        result = self._keyword_scan(text_lower, text_clean)
        if result:
            logger.info(
                "Intent routed via keywords",
                extra={
                    "intent":     result.intent.value,
                    "use_llm":    result.use_llm,
                    "tool":       result.tool.value if result.tool else None,
                    "confidence": result.confidence,
                }
            )
            return result

        # Stage 2 — fallback to conversation
        logger.info(
            "Intent routed to conversation",
            extra={"intent": INTENT.CONVERSATION.value}
        )
        return RouteResult(
            intent=INTENT.CONVERSATION,
            use_llm=True,
            tool=None,
            confidence=0.6,
            raw_input=text_clean,
        )

    # ── Stage 1: Keyword scan ─────────────────────────────────────

    def _keyword_scan(self, text_lower: str, raw: str) -> RouteResult | None:
        """
        Scans for known trigger keywords.
        Multi-word keywords checked first (higher priority).
        """
        # Sort by length descending — match "band kar" before "band"
        sorted_keywords = sorted(
            self._keyword_index.keys(),
            key=len,
            reverse=True,
        )

        for keyword in sorted_keywords:
            if keyword in text_lower:
                intent = self._keyword_index[keyword]
                return self._build_result(intent, raw, text_lower)

        return None

    # ── Stage 2: Build result with extracted params ───────────────

    def _build_result(
        self,
        intent:     INTENT,
        raw:        str,
        text_lower: str,
    ) -> RouteResult:
        """
        Given a matched intent, extract parameters via regex
        and decide whether the LLM is needed.
        """

        # ── Music ─────────────────────────────────────────────────
        if intent == INTENT.MUSIC_PLAY:
            params = self._extract_music_params(raw)
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.95,
                raw_input=raw,
            )

        if intent in (INTENT.MUSIC_PAUSE, INTENT.MUSIC_STOP, INTENT.MUSIC_NEXT):
            return RouteResult(
                intent=intent,
                params={},
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.98,
                raw_input=raw,
            )

        # ── GitHub ────────────────────────────────────────────────
        if intent == INTENT.GITHUB_CREATE:
            params = self._extract_github_create_params(raw)
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=bool(not params.get("repo_name")),
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.92,
                raw_input=raw,
            )

        if intent == INTENT.GITHUB_PUSH:
            params = self._extract_github_push_params(raw)
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.90,
                raw_input=raw,
            )

        if intent == INTENT.GITHUB_LIST:
            return RouteResult(
                intent=intent,
                params={},
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.98,
                raw_input=raw,
            )

        # ── Browser ───────────────────────────────────────────────
        if intent == INTENT.BROWSER_OPEN:
            params = self._extract_browser_params(raw)
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.90,
                raw_input=raw,
            )

        # ── Web search ────────────────────────────────────────────
        if intent == INTENT.WEB_SEARCH:
            params = self._extract_search_params(raw)
            # LLM synthesises the results into a proper answer
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=True,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.93,
                raw_input=raw,
            )

        # ── Code ──────────────────────────────────────────────────
        if intent == INTENT.CODE_RUN:
            return RouteResult(
                intent=intent,
                params={"raw": raw},
                use_llm=False,
                tool=DIRECT_TOOL_INTENTS.get(intent),
                confidence=0.88,
                raw_input=raw,
            )

        # ── Memory ────────────────────────────────────────────────
        if intent == INTENT.MEMORY_SAVE:
            return RouteResult(
                intent=intent,
                params={"content": raw},
                use_llm=False,
                tool=None,
                confidence=0.90,
                raw_input=raw,
            )

        if intent == INTENT.MEMORY_RECALL:
            return RouteResult(
                intent=intent,
                params={"query": raw},
                use_llm=True,
                tool=None,
                confidence=0.88,
                raw_input=raw,
            )

        # ── Personality switch ────────────────────────────────────
        if intent == INTENT.PERSONALITY_SWITCH:
            params = self._extract_personality_params(raw)
            return RouteResult(
                intent=intent,
                params=params,
                use_llm=False,
                tool=None,
                confidence=0.95,
                raw_input=raw,
            )

        # ── ICARUS system ─────────────────────────────────────────
        if intent in (INTENT.ICARUS_STATUS, INTENT.ICARUS_HELP):
            return RouteResult(
                intent=intent,
                params={},
                use_llm=True,
                tool=None,
                confidence=0.95,
                raw_input=raw,
            )

        # ── Default: LLM handles it ───────────────────────────────
        return RouteResult(
            intent=intent,
            params={},
            use_llm=intent in LLM_ASSISTED_INTENTS,
            tool=DIRECT_TOOL_INTENTS.get(intent),
            confidence=0.75,
            raw_input=raw,
        )

    # ── Parameter extractors ──────────────────────────────────────

    def _extract_music_params(self, text: str) -> dict:
        match = _MUSIC_PLAY_PATTERN.search(text)
        if match:
            query = match.group(1).strip()
            # Clean trailing filler words
            query = re.sub(
                r"\s*(please|kar do|karo|de|na|bhai|yaar)\s*$",
                "",
                query,
                flags=re.IGNORECASE,
            ).strip()
            return {"query": query}
        return {"query": text}

    def _extract_github_create_params(self, text: str) -> dict:
        match = _GITHUB_CREATE_PATTERN.search(text)
        if match:
            return {"repo_name": match.group(1).strip()}
        return {}

    def _extract_github_push_params(self, text: str) -> dict:
        match = _GITHUB_PUSH_PATTERN.search(text)
        if match and match.group(1):
            return {"repo_name": match.group(1).strip()}
        return {}

    def _extract_browser_params(self, text: str) -> dict:
        match = _BROWSER_OPEN_PATTERN.search(text)
        if match:
            target = match.group(1).strip()
            # Detect if it's a URL or an app name
            is_url = any(
                x in target.lower()
                for x in ["http", "www.", ".com", ".in", ".org", ".io"]
            )
            return {"target": target, "is_url": is_url}
        return {"target": text, "is_url": False}

    def _extract_search_params(self, text: str) -> dict:
        match = _SEARCH_PATTERN.search(text)
        if match:
            return {"query": match.group(1).strip()}
        return {"query": text}

    def _extract_personality_params(self, text: str) -> dict:
        match = _PERSONALITY_PATTERN.search(text)
        if match:
            raw_name = match.group(1).lower().strip()
            profile  = _PERSONALITY_MAP.get(raw_name, raw_name)
            return {"profile": profile}
        return {}


# ── Singleton ──────────────────────────────────────────────────────
router = IntentRouter()