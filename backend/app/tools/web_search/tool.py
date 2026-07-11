"""
ICARUS Web Search Tool
=======================
Real-time web search via DuckDuckGo. No API key needed.
Results are returned as structured data and synthesised by LLM.

Triggers:
  "search Python tutorials"
  "kya hai quantum computing"
  "latest news about AI"
"""

import logging
import asyncio

from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):

    MAX_RESULTS = 5

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for real-time information using DuckDuckGo"

    @property
    def triggers(self) -> list[str]:
        return [
            "search", "find", "look up", "google",
            "dhundh", "batao", "kya hai", "latest",
        ]

    async def execute(self, input: str, context: dict) -> ToolResult:
        params = context.get("params", {})
        query  = params.get("query", input).strip()

        if not query:
            return ToolResult(
                success=False,
                output=None,
                message="No search query provided",
                tool_name=self.name,
            )

        return await self._search(query)

    async def _search(self, query: str) -> ToolResult:
        """Run DuckDuckGo search and return structured results."""
        try:
            from duckduckgo_search import DDGS

            loop    = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=self.MAX_RESULTS))
            )

            if not results:
                return ToolResult(
                    success=True,
                    output=[],
                    message=f"No results found for: {query}",
                    tool_name=self.name,
                )

            # Format results cleanly for LLM consumption
            formatted = []
            for r in results:
                formatted.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url":     r.get("href", ""),
                })

            # Build a clean text block for LLM context
            text_block = f"Search results for: {query}\n\n"
            for i, r in enumerate(formatted, 1):
                text_block += f"{i}. {r['title']}\n{r['snippet']}\nSource: {r['url']}\n\n"

            logger.info(
                "Web search complete",
                extra={"query": query, "results": len(formatted)}
            )

            return ToolResult(
                success=True,
                output={
                    "query":      query,
                    "results":    formatted,
                    "text_block": text_block,
                },
                message=f"Found {len(formatted)} results for '{query}'",
                tool_name=self.name,
            )

        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                message="duckduckgo-search not installed. Run: pip install duckduckgo-search",
                tool_name=self.name,
            )
        except Exception as e:
            logger.error("Web search error", extra={"error": str(e)})
            return ToolResult(
                success=False,
                output=None,
                message=f"Search failed: {str(e)}",
                tool_name=self.name,
            )