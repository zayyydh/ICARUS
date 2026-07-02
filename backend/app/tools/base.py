"""
BaseTool — every ICARUS tool implements this interface.
Adding a new tool = create a new folder, implement BaseTool, done.
The brain never knows which tool it calls — just execute().
"""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any

class ToolResult(BaseModel):
    success: bool
    output: Any
    message: str
    tool_name: str

class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier e.g. 'github', 'music', 'browser'"""

    @property
    @abstractmethod
    def description(self) -> str:
        """One line — what this tool does"""

    @property
    @abstractmethod
    def triggers(self) -> list[str]:
        """Intent keywords that route to this tool"""

    @abstractmethod
    async def execute(self, input: str, context: dict) -> ToolResult:
        """Run the tool. Always returns ToolResult."""
