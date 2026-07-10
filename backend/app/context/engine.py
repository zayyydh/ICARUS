"""
ICARUS Context Engine
======================
Auto-switches personality based on time of day and active apps.
ICARUS adapts to your context — you never have to ask it to.

Examples:
  8 AM  + VS Code open    → Developer mode
  3 PM  + LeetCode open   → Coach mode
  11 PM + Spotify open    → Night Owl mode
  Any   + Discord open    → Bro mode

Usage:
    from app.context.engine import context_engine
    profile = await context_engine.detect()
    # Returns suggested personality name
"""

import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass

from app.config.constants import PERSONALITY, PERSONALITY_CONTEXT_TRIGGERS
from app.config.settings import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# CONTEXT SNAPSHOT
# ══════════════════════════════════════════════════════════════════

@dataclass
class ContextSnapshot:
    """
    A point-in-time snapshot of the user's environment.
    Collected by detectors and used to decide personality.
    """
    hour:         int         # 0-23
    active_apps:  list[str]   # lowercase app names currently running
    personality:  str         # suggested personality
    reason:       str         # why this personality was chosen


# ══════════════════════════════════════════════════════════════════
# APP DETECTOR
# Detects which apps are currently running on Windows
# ══════════════════════════════════════════════════════════════════

class AppDetector:
    """
    Detects running processes on Windows.
    Uses psutil for cross-platform process listing.
    Gracefully degrades if psutil isn't installed.
    """

    # Maps process names → canonical app names
    # Process names vary by OS — we normalise them
    PROCESS_MAP = {
        # Code editors
        "code.exe":          "vscode",
        "code":              "vscode",
        "pycharm64.exe":     "pycharm",
        "pycharm":           "pycharm",
        "cursor.exe":        "cursor",
        "vim":               "vim",
        "nvim":              "vim",
        "sublime_text.exe":  "sublime",

        # Terminals
        "windowsterminal.exe": "terminal",
        "cmd.exe":             "terminal",
        "powershell.exe":      "terminal",
        "wt.exe":              "terminal",
        "bash":                "terminal",
        "zsh":                 "terminal",

        # Browsers
        "chrome.exe":         "chrome",
        "firefox.exe":        "firefox",
        "msedge.exe":         "edge",
        "brave.exe":          "brave",

        # Communication
        "discord.exe":        "discord",
        "discord":            "discord",
        "slack.exe":          "slack",
        "teams.exe":          "teams",
        "whatsapp.exe":       "whatsapp",

        # Music
        "spotify.exe":        "spotify",
        "spotify":            "spotify",

        # Gaming
        "steam.exe":          "steam",
        "epicgameslauncher.exe": "steam",

        # Productivity
        "notion.exe":         "notion",
        "obsidian.exe":       "obsidian",
        "anki.exe":           "anki",

        # Study / practice
        "leetcode":           "leetcode",
    }

    # Browser-based apps we detect via window titles
    # (can't detect via process name — they all run in chrome.exe)
    BROWSER_APP_KEYWORDS = {
        "leetcode":   "leetcode",
        "github":     "github",
        "notion":     "notion",
        "youtube":    "youtube",
        "spotify":    "spotify",
    }

    async def get_running_apps(self) -> list[str]:
        """
        Returns list of canonical app names currently running.
        Non-blocking — runs in thread pool.
        """
        try:
            import psutil
            loop = asyncio.get_event_loop()
            apps = await loop.run_in_executor(None, self._scan_processes)
            return apps
        except ImportError:
            logger.debug("psutil not installed — app detection unavailable")
            return []
        except Exception as e:
            logger.warning(
                "App detection failed",
                extra={"error": str(e)}
            )
            return []

    def _scan_processes(self) -> list[str]:
        """Synchronous process scan — run via executor."""
        import psutil
        found = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"].lower()
                if name in self.PROCESS_MAP:
                    found.add(self.PROCESS_MAP[name])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return list(found)


# ══════════════════════════════════════════════════════════════════
# TIME DETECTOR
# ══════════════════════════════════════════════════════════════════

class TimeDetector:
    """
    Returns the current hour and time-based personality suggestion.
    """

    TIME_PERIODS = {
        "early_morning": range(5, 9),    # 5 AM - 8 AM
        "morning":       range(9, 12),   # 9 AM - 11 AM
        "afternoon":     range(12, 17),  # 12 PM - 4 PM
        "evening":       range(17, 21),  # 5 PM - 8 PM
        "night":         range(21, 24),  # 9 PM - 11 PM
        "late_night":    range(0, 5),    # 12 AM - 4 AM
    }

    def get_hour(self) -> int:
        return datetime.now().hour

    def get_period(self) -> str:
        hour = self.get_hour()
        for period, hours in self.TIME_PERIODS.items():
            if hour in hours:
                return period
        return "afternoon"

    def suggest_personality(self) -> str | None:
        """
        Suggest a personality based purely on time.
        Returns None if no strong time-based suggestion.
        """
        period = self.get_period()
        suggestions = {
            "late_night":    PERSONALITY.NIGHT_OWL.value,
            "night":         PERSONALITY.NIGHT_OWL.value,
            "early_morning": PERSONALITY.MINIMALIST.value,
        }
        return suggestions.get(period)


# ══════════════════════════════════════════════════════════════════
# CONTEXT ENGINE
# ══════════════════════════════════════════════════════════════════

class ContextEngine:
    """
    Combines app detection + time detection to suggest
    the most appropriate personality for the current moment.

    Priority order (highest wins):
      1. App-based detection  (most specific signal)
      2. Time-based detection (fallback)
      3. Default personality  (always available)
    """

    def __init__(self):
        self.app_detector  = AppDetector()
        self.time_detector = TimeDetector()
        self._last_snapshot: ContextSnapshot | None = None
        logger.info("Context engine initialized")

    async def detect(self) -> ContextSnapshot:
        """
        Detect current context and return suggested personality.
        Called periodically to keep personality fresh.
        """
        hour        = self.time_detector.get_hour()
        active_apps = await self.app_detector.get_running_apps()

        logger.debug(
            "Context detected",
            extra={"hour": hour, "apps": active_apps}
        )

        # Priority 1 — app-based personality
        app_result = self._match_app(active_apps)
        if app_result:
            personality, reason = app_result
            snapshot = ContextSnapshot(
                hour=hour,
                active_apps=active_apps,
                personality=personality,
                reason=reason,
            )
            self._last_snapshot = snapshot
            return snapshot

        # Priority 2 — time-based personality
        time_suggestion = self.time_detector.suggest_personality()
        if time_suggestion:
            snapshot = ContextSnapshot(
                hour=hour,
                active_apps=active_apps,
                personality=time_suggestion,
                reason=f"Time-based: {self.time_detector.get_period()} mode",
            )
            self._last_snapshot = snapshot
            return snapshot

        # Priority 3 — default
        snapshot = ContextSnapshot(
            hour=hour,
            active_apps=active_apps,
            personality=settings.DEFAULT_PERSONALITY,
            reason="Default personality",
        )
        self._last_snapshot = snapshot
        return snapshot

    def _match_app(self, active_apps: list[str]) -> tuple[str, str] | None:
        """
        Match running apps against personality triggers.
        Returns (personality_name, reason) or None.
        """
        for personality, triggers in PERSONALITY_CONTEXT_TRIGGERS.items():
            app_triggers = triggers.get("apps", [])
            for app in active_apps:
                if app in app_triggers:
                    return (
                        personality.value,
                        f"App detected: {app} → {personality.value} mode"
                    )
        return None

    async def should_switch(self, current_personality: str) -> tuple[bool, str]:
        """
        Check if personality should switch given current context.
        Returns (should_switch, suggested_personality).

        Called by Orchestrator periodically to keep personality fresh.
        """
        if not settings.PERSONALITY_AUTO_SWITCH:
            return False, current_personality

        snapshot = await self.detect()

        if snapshot.personality != current_personality:
            logger.info(
                "Context suggests personality switch",
                extra={
                    "current":   current_personality,
                    "suggested": snapshot.personality,
                    "reason":    snapshot.reason,
                }
            )
            return True, snapshot.personality

        return False, current_personality

    @property
    def last_snapshot(self) -> ContextSnapshot | None:
        return self._last_snapshot


# ── Singleton ──────────────────────────────────────────────────────
context_engine = ContextEngine()