"""
ICARUS Chat endpoint — v3
==========================
Now session-aware and memory-backed.
Pass a session_id to maintain conversation across requests.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.brain.orchestrator import orchestrator
from app.config.constants import ICARUS_NAME

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role:    str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32_000)

class ChatRequest(BaseModel):
    message:     str               = Field(..., min_length=1, max_length=8_000)
    session_id:  str               = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    history:     list[ChatMessage] = Field(default_factory=list)
    language:    str               = Field(default="hinglish")
    personality: str               = Field(default="bro")

class ChatResponse(BaseModel):
    reply:       str
    intent:      str
    used_llm:    bool
    used_tool:   str | None
    tokens_used: int
    personality: str
    language:    str
    session_id:  str

class QuickRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4_000)
    system: str = Field(default="")

class QuickResponse(BaseModel):
    reply: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, summary="Chat with ICARUS")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main ICARUS chat endpoint.
    Pass the same session_id across requests to maintain memory.
    ICARUS remembers your conversation history automatically.
    """
    logger.info(
        "Chat request",
        extra={
            "session_id":  request.session_id,
            "language":    request.language,
            "personality": request.personality,
        }
    )

    history = [
        {"role": m.role, "content": m.content}
        for m in request.history
    ]

    try:
        response = await orchestrator.handle(
            text=request.message,
            language=request.language,
            personality=request.personality,
            history=history,
            session_id=request.session_id,
        )

        return ChatResponse(
            reply=response.text,
            intent=response.intent,
            used_llm=response.used_llm,
            used_tool=response.used_tool,
            tokens_used=response.tokens_used,
            personality=response.personality,
            language=response.language,
            session_id=response.session_id,
        )

    except Exception as e:
        logger.error("Chat error", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"{ICARUS_NAME} error: {str(e)}"
        )


@router.post("/quick", response_model=QuickResponse, summary="One-shot prompt")
async def quick_chat(request: QuickRequest) -> QuickResponse:
    try:
        from app.llm.manager import llm
        reply = await llm.quick(request.prompt, system=request.system)
        return QuickResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))