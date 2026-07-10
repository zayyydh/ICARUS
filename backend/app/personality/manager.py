"""
ICARUS Personality Engine
==========================
Loads JSON personality profiles and builds dynamic system prompts.

Every LLM call gets a personality-aware system prompt injected.
Personalities are data, not hardcoded strings — easy to add new ones,
easy to share, easy to customize.

Usage:
    from app.personality.manager import personality_manager
    prompt = personality_manager.build_prompt("bro", "hinglish")
"""

import json
import logging
import random
from pathlib import Path
from functools import lru_cache

from app.config.settings import settings
from app.config.constants import PERSONALITY

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# PERSONALITY PROFILE SCHEMA
# ══════════════════════════════════════════════════════════════════

class PersonalityProfile:
    """
    Represents a loaded personality profile.
    Wraps the JSON data with convenient accessors.
    """

    def __init__(self, data: dict):
        self.name           = data["name"]
        self.description    = data.get("description", "")
        self.humor          = data.get("humor", 50)          # 0-100
        self.sarcasm        = data.get("sarcasm", 10)        # 0-100
        self.confidence     = data.get("confidence", 85)     # 0-100
        self.verbosity      = data.get("verbosity", "medium")
        self.emoji          = data.get("emoji", False)
        self.slang          = data.get("slang", False)
        self.hinglish       = data.get("hinglish", False)
        self.voice_speed    = data.get("voice_speed", 1.0)
        self.thinking_style = data.get("thinking_style", "balanced")
        self.triggers       = data.get("triggers", [])
        self.greeting       = data.get("greeting", "Ready.")
        self.tone_adjectives= data.get("tone_adjectives", [])
        self._raw           = data

    def __repr__(self) -> str:
        return f"PersonalityProfile(name={self.name}, humor={self.humor})"


# ══════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# Converts personality data → system prompt instructions
# ══════════════════════════════════════════════════════════════════

class PromptBuilder:
    """
    Converts a PersonalityProfile into a system prompt section
    that gets injected into every Gemini call.
    """

    def build(self, profile: PersonalityProfile, language: str) -> str:
        """
        Build the personality section of the system prompt.
        This gets appended to the base ICARUS system prompt.
        """
        lines = [
            f"━━━ ACTIVE PERSONALITY: {profile.name.upper()} ━━━",
            f"Description: {profile.description}",
            "",
            "Tone and style:",
        ]

        # Humor
        if profile.humor >= 70:
            lines.append("- Be genuinely funny and light-hearted when appropriate")
        elif profile.humor >= 40:
            lines.append("- Occasional wit is fine but don't force humor")
        else:
            lines.append("- Keep it professional — humor only if very natural")

        # Sarcasm
        if profile.sarcasm >= 40:
            lines.append("- Light sarcasm is acceptable with close context")
        else:
            lines.append("- Avoid sarcasm entirely")

        # Verbosity
        verbosity_map = {
            "minimal": "- One sentence maximum unless more is explicitly asked for",
            "low":     "- Keep responses short — 2-3 sentences max for simple things",
            "medium":  "- Match response length to question complexity",
            "high":    "- Be thorough and detailed — explain your reasoning",
        }
        lines.append(
            verbosity_map.get(profile.verbosity, verbosity_map["medium"])
        )

        # Confidence
        if profile.confidence >= 90:
            lines.append("- Be decisive and direct — no hedging")
        elif profile.confidence >= 70:
            lines.append("- Be reasonably confident but acknowledge uncertainty")
        else:
            lines.append("- Be careful and measured — acknowledge when unsure")

        # Language style
        if profile.hinglish and language in ("hinglish", "hi"):
            lines.append(
                "- USE HINGLISH naturally — mix Hindi and English the way "
                "desi people actually talk. 'Haan bhai', 'theek hai', "
                "'bas kar', 'kya scene hai' etc."
            )
        if profile.slang:
            lines.append(
                "- Use Indian slang naturally: yaar, bhai, arre, pakka, "
                "mast, bindaas, sahi hai etc."
            )

        # Thinking style
        thinking_map = {
            "analytical":    "- Think step-by-step for technical problems",
            "casual":        "- Think out loud casually like talking to a friend",
            "pedagogical":   "- Always explain the 'why', not just the 'what'",
            "motivational":  "- Frame everything with energy and forward momentum",
            "relaxed":       "- Keep it chill — no urgency, no pressure",
            "minimal":       "- Answer only what was asked. Nothing extra.",
        }
        style = thinking_map.get(profile.thinking_style, "")
        if style:
            lines.append(style)

        # Tone adjectives
        if profile.tone_adjectives:
            adj_str = ", ".join(profile.tone_adjectives)
            lines.append(f"- Your tone should be: {adj_str}")

        # Emoji
        if not profile.emoji:
            lines.append("- Do NOT use emojis")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# PERSONALITY MANAGER
# ══════════════════════════════════════════════════════════════════

class PersonalityManager:
    """
    Loads all personality profiles from JSON files.
    Builds system prompt sections on demand.
    Manages the active personality state.
    """

    def __init__(self):
        self._profiles:  dict[str, PersonalityProfile] = {}
        self._builder    = PromptBuilder()
        self._active     = settings.DEFAULT_PERSONALITY
        self._load_all()

    def _load_all(self) -> None:
        """Load every JSON file from the profiles directory."""
        profiles_dir = settings.PROFILES_DIR

        if not profiles_dir.exists():
            logger.warning(
                "Profiles directory not found",
                extra={"path": str(profiles_dir)}
            )
            self._load_fallback_profiles()
            return

        loaded = 0
        for json_file in profiles_dir.glob("*.json"):
            try:
                data    = json.loads(json_file.read_text(encoding="utf-8"))
                key     = json_file.stem   # filename without .json
                profile = PersonalityProfile(data)
                self._profiles[key] = profile
                loaded += 1
                logger.debug(
                    "Personality profile loaded",
                    extra={"profile": key}
                )
            except Exception as e:
                logger.error(
                    "Failed to load personality profile",
                    extra={"file": json_file.name, "error": str(e)}
                )

        if loaded == 0:
            logger.warning("No profiles loaded from disk — using fallbacks")
            self._load_fallback_profiles()
        else:
            logger.info(
                "Personality profiles loaded",
                extra={"count": loaded, "profiles": list(self._profiles.keys())}
            )

    def _load_fallback_profiles(self) -> None:
        """
        Minimal hardcoded profiles used when JSON files aren't found.
        Ensures ICARUS always has at least one personality.
        """
        self._profiles["bro"] = PersonalityProfile({
            "name":           "Bro",
            "description":    "Casual, Hinglish-friendly daily companion",
            "humor":          75,
            "sarcasm":        30,
            "confidence":     85,
            "verbosity":      "low",
            "emoji":          False,
            "slang":          True,
            "hinglish":       True,
            "voice_speed":    1.05,
            "thinking_style": "casual",
            "triggers":       ["discord", "default"],
            "greeting":       "Haan bhai, bol kya scene hai?",
            "tone_adjectives": ["warm", "casual", "desi"],
        })
        self._profiles["developer"] = PersonalityProfile({
            "name":           "Developer",
            "description":    "Precise, technical, code-focused",
            "humor":          20,
            "sarcasm":        10,
            "confidence":     90,
            "verbosity":      "medium",
            "emoji":          False,
            "slang":          False,
            "hinglish":       False,
            "voice_speed":    1.0,
            "thinking_style": "analytical",
            "triggers":       ["vscode", "terminal"],
            "greeting":       "Ready. What are we building?",
            "tone_adjectives": ["precise", "direct", "technical"],
        })
        logger.info("Fallback personalities loaded", extra={"count": 2})

    # ── Public API ────────────────────────────────────────────────

    @property
    def active(self) -> str:
        return self._active

    @property
    def active_profile(self) -> PersonalityProfile:
        return self._profiles.get(
            self._active,
            self._profiles.get("bro")
        )

    def switch(self, profile_name: str) -> bool:
        """
        Switch to a different personality.
        Returns True if successful, False if profile not found.
        """
        if profile_name not in self._profiles:
            logger.warning(
                "Unknown personality profile",
                extra={"requested": profile_name, "available": list(self._profiles)}
            )
            return False

        old = self._active
        self._active = profile_name
        logger.info(
            "Personality switched",
            extra={"from": old, "to": profile_name}
        )
        return True

    def get_profile(self, name: str) -> PersonalityProfile | None:
        return self._profiles.get(name)

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    def build_prompt(self, profile_name: str, language: str) -> str:
        """
        Build the personality system prompt section.
        Called by the LLM Manager before every Gemini call.
        """
        profile = self._profiles.get(profile_name) or self.active_profile
        return self._builder.build(profile, language)

    def get_greeting(self, profile_name: str | None = None) -> str:
        """Get the greeting line for a personality (used at boot)."""
        name    = profile_name or self._active
        profile = self._profiles.get(name)
        if not profile:
            return "ICARUS online."
        return profile.greeting

    def get_random_boot_line(self) -> str:
        """Pick a random boot greeting from the active personality."""
        profile = self.active_profile
        greetings = [
            profile.greeting,
            "Online. Ready when you are.",
            "All systems operational.",
        ]
        return random.choice(greetings)


# ── Singleton ──────────────────────────────────────────────────────
personality_manager = PersonalityManager()