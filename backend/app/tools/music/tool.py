"""
ICARUS Music Tool
==================
Plays music from YouTube by opening it in the default browser.
No API key needed — uses a direct YouTube search URL.

Phase 2: swap browser open for yt-dlp + pygame for actual audio.

Triggers:
  "play Kesariya"         → opens YouTube search
  "gana baja Tum Hi Ho"   → opens YouTube search
  "pause"                 → pauses if yt-dlp active
"""

import logging
import webbrowser
import urllib.parse

from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class MusicTool(BaseTool):

    @property
    def name(self) -> str:
        return "music"

    @property
    def description(self) -> str:
        return "Play music from YouTube by voice command"

    @property
    def triggers(self) -> list[str]:
        return [
            "play", "gana", "gaana", "song", "music",
            "baja", "laga", "bajao", "chalao",
        ]

    async def execute(self, input: str, context: dict) -> ToolResult:
        intent = context.get("intent", "music_play")
        params = context.get("params", {})

        if "pause" in intent:
            return self._pause()
        if "stop" in intent:
            return self._stop()
        if "next" in intent:
            return self._next()

        # Default — play
        query = params.get("query", input)
        return self._play(query)

    def _play(self, query: str) -> ToolResult:
        """Open YouTube search for the requested song."""
        if not query or not query.strip():
            return ToolResult(
                success=False,
                output=None,
                message="No song specified. Say: 'play Kesariya'",
                tool_name=self.name,
            )

        # Build YouTube search URL
        encoded   = urllib.parse.quote(query)
        url       = f"https://www.youtube.com/results?search_query={encoded}"

        try:
            webbrowser.open(url)
            logger.info("Music playing", extra={"query": query, "url": url})
            return ToolResult(
                success=True,
                output={"query": query, "url": url},
                message=f"Opening YouTube for '{query}'",
                tool_name=self.name,
            )
        except Exception as e:
            logger.error("Music tool error", extra={"error": str(e)})
            return ToolResult(
                success=False,
                output=None,
                message=f"Could not open browser: {str(e)}",
                tool_name=self.name,
            )

    def _pause(self) -> ToolResult:
        return ToolResult(
            success=True,
            output=None,
            message="Pause support coming in Phase 4 with yt-dlp",
            tool_name=self.name,
        )

    def _stop(self) -> ToolResult:
        return ToolResult(
            success=True,
            output=None,
            message="Stop support coming in Phase 4 with yt-dlp",
            tool_name=self.name,
        )

    def _next(self) -> ToolResult:
        return ToolResult(
            success=True,
            output=None,
            message="Next track support coming in Phase 4 with yt-dlp",
            tool_name=self.name,
        )