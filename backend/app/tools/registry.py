"""
ICARUS Tool Registry
=====================
Auto-discovers and manages all tool plugins.

Adding a new tool to ICARUS:
  1. Create backend/app/tools/your_tool/tool.py
  2. Implement BaseTool
  3. Done — registry finds it automatically on next startup

No hardcoding. No manual registration. Just drop it in.

Usage:
    from app.tools.registry import tool_registry
    tool = tool_registry.get("music")
    result = await tool.execute("play Kesariya", {})
"""

import importlib
import logging
from pathlib import Path

from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Discovers and holds all ICARUS tool implementations.
    Scans the tools/ directory on startup.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def discover(self) -> None:
        """
        Scan tools/ directory and import every tool.py found.
        Called once at startup from main.py lifespan.
        """
        tools_dir = Path(__file__).parent

        for tool_dir in sorted(tools_dir.iterdir()):
            # Only look at subdirectories with a tool.py
            if not tool_dir.is_dir():
                continue
            if tool_dir.name.startswith("_"):
                continue
            tool_file = tool_dir / "tool.py"
            if not tool_file.exists():
                continue

            # Build the module path e.g. app.tools.music.tool
            module_path = f"app.tools.{tool_dir.name}.tool"

            try:
                module = importlib.import_module(module_path)

                # Find the BaseTool subclass in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        instance = attr()
                        self._tools[instance.name] = instance
                        logger.info(
                            "Tool registered",
                            extra={"tool": instance.name, "module": module_path}
                        )
                        break

            except Exception as e:
                logger.warning(
                    "Failed to load tool",
                    extra={"dir": tool_dir.name, "error": str(e)}
                )

        logger.info(
            "Tool discovery complete",
            extra={"tools": list(self._tools.keys())}
        )

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def all(self) -> dict[str, BaseTool]:
        """Return all registered tools."""
        return dict(self._tools)

    def names(self) -> list[str]:
        """Return list of all registered tool names."""
        return list(self._tools.keys())

    async def execute(
        self,
        tool_name: str,
        input:     str,
        context:   dict | None = None,
    ) -> ToolResult:
        """
        Execute a tool by name.
        Returns a failed ToolResult if the tool isn't found.
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                message=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
            )
        return await tool.execute(input, context or {})

    def describe_all(self) -> list[dict]:
        """
        Return descriptions of all tools.
        Used to tell the LLM what tools are available.
        """
        return [
            {
                "name":        t.name,
                "description": t.description,
                "triggers":    t.triggers,
            }
            for t in self._tools.values()
        ]


# ── Singleton ──────────────────────────────────────────────────────
tool_registry = ToolRegistry()