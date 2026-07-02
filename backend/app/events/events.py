"""
ICARUS Event definitions.
Components communicate through events — not direct calls.

Flow example:
  User speaks → SpeechRecognizedEvent → Brain
  Brain responds → ResponseGeneratedEvent → Voice Engine
"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IcarusEvent:
    timestamp: datetime = None
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

@dataclass
class SpeechRecognizedEvent(IcarusEvent):
    text: str = ""
    language: str = "en"
    confidence: float = 1.0

@dataclass
class IntentDetectedEvent(IcarusEvent):
    intent: str = ""
    raw_input: str = ""
    tool: str = None

@dataclass
class ResponseGeneratedEvent(IcarusEvent):
    text: str = ""
    language: str = "en"
    personality: str = "bro"

@dataclass
class ToolExecutedEvent(IcarusEvent):
    tool_name: str = ""
    success: bool = True
    output: str = ""
