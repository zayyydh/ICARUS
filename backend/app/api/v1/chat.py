"""
ICARUS Chat endpoint
=====================
The first real ICARUS capability — text conversation.
Voice comes later. This is the brain speaking through text.

POST /api/v1/chat        → send a message, get a response
POST /api/v1/chat/quick  → one-shot prompt, no history
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.manager import llm
from app.llm.base import Message, Role, LLMConfig
from app.config.settings import settings
from app.config.constants import ICARUS_NAME

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


# ── Request / Response schemas ─────────────────────────────────────

class ChatMessage(BaseModel):
    role:    str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32_000)

class ChatRequest(BaseModel):
    message:     str              = Field(..., min_length=1, max_length=8_000)
    history:     list[ChatMessage] = Field(default_factory=list)
    language:    str              = Field(default="hinglish")
    personality: str              = Field(default="bro")

class ChatResponse(BaseModel):
    reply:       str
    provider:    str
    model:       str
    tokens_used: int
    personality: str
    language:    str

class QuickRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4_000)
    system: str = Field(default="")

class QuickResponse(BaseModel):
    reply: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with ICARUS",
    description="Send a message with conversation history. ICARUS replies in your language.",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main ICARUS chat endpoint.
    Accepts conversation history so ICARUS remembers
    what was said earlier in the session.
    """
    logger.info(
        "Chat request received",
        extra={
            "language":    request.language,
            "personality": request.personality,
            "history_len": len(request.history),
        }
    )

    # Build message list from history + new message
    messages: list[Message] = []

    for h in request.history:
        role = Role.USER if h.role == "user" else Role.ASSISTANT
        messages.append(Message(role=role, content=h.content))

    # Add the new user message
    messages.append(Message(role=Role.USER, content=request.message))

    try:
        response = await llm.chat(
            messages=messages,
            personality=request.personality,
            language=request.language,
        )

        logger.info(
            "Chat response sent",
            extra={"tokens": response.total_tokens}
        )

        return ChatResponse(
            reply=response.content,
            provider=response.provider,
            model=response.model,
            tokens_used=response.total_tokens,
            personality=request.personality,
            language=request.language,
        )

    except Exception as e:
        logger.error("Chat failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"{ICARUS_NAME} encountered an error: {str(e)}"
        )


@router.post(
    "/quick",
    response_model=QuickResponse,
    summary="One-shot prompt",
    description="Send a single prompt with no history. Fast, simple.",
)
async def quick_chat(request: QuickRequest) -> QuickResponse:
    """
    One-shot endpoint — no history, just prompt → reply.
    Used internally by tools that need a quick LLM call.
    """
    try:
        reply = await llm.quick(request.prompt, system=request.system)
        return QuickResponse(reply=reply)
    except Exception as e:
        logger.error("Quick chat failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))