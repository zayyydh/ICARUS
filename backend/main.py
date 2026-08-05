"""
ICARUS — Production Entry Point
Ultra-minimal, guaranteed to stay up on Railway.
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("icarus")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Project ICARUS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health — always first, no dependencies ─────────────────────────
@app.get("/api/v1/health")
async def health():
    return {"status": "online", "system": "ICARUS", "version": "0.1.0"}

@app.get("/")
async def root():
    return {"status": "online", "docs": "/docs"}

logger.info(f"ICARUS starting on port {os.getenv('PORT', '8000')}")

# ── LLM — lazy load ────────────────────────────────────────────────
_llm = None
def get_llm():
    global _llm
    if _llm is None:
        try:
            from app.llm.manager import llm
            _llm = llm
            logger.info("LLM loaded")
        except Exception as e:
            logger.error(f"LLM load failed: {e}")
    return _llm

# ── Orchestrator — lazy load ───────────────────────────────────────
_orch = None
def get_orch():
    global _orch
    if _orch is None:
        try:
            from app.brain.orchestrator import orchestrator
            _orch = orchestrator
            logger.info("Orchestrator loaded")
        except Exception as e:
            logger.error(f"Orchestrator load failed: {e}")
    return _orch

# ── Tool registry — lazy load ──────────────────────────────────────
_tools_loaded = False
def load_tools():
    global _tools_loaded
    if not _tools_loaded:
        try:
            from app.tools.registry import tool_registry
            tool_registry.discover()
            logger.info(f"Tools: {tool_registry.names()}")
            _tools_loaded = True
        except Exception as e:
            logger.error(f"Tools load failed: {e}")

# ── Chat schema ────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "hinglish"
    personality: Optional[str] = "bro"
    history: Optional[list] = []

@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    load_tools()
    orch = get_orch()
    llm  = get_llm()

    def err_resp(msg):
        return {
            "reply": msg, "intent": "error",
            "used_llm": False, "used_tool": None,
            "tokens_used": 0,
            "personality": req.personality,
            "language": req.language,
            "session_id": req.session_id,
        }

    if orch:
        try:
            r = await orch.handle(
                text=req.message,
                language=req.language,
                personality=req.personality,
                session_id=req.session_id,
            )
            return {
                "reply": r.text, "intent": r.intent,
                "used_llm": r.used_llm, "used_tool": r.used_tool,
                "tokens_used": r.tokens_used,
                "personality": r.personality,
                "language": r.language,
                "session_id": r.session_id,
            }
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return err_resp(f"Error: {str(e)}")

    if llm:
        try:
            from app.llm.base import Message, Role
            resp = await llm.chat(
                messages=[Message(role=Role.USER, content=req.message)],
                personality=req.personality,
                language=req.language,
            )
            return {
                "reply": resp.content, "intent": "conversation",
                "used_llm": True, "used_tool": None,
                "tokens_used": resp.total_tokens,
                "personality": req.personality,
                "language": req.language,
                "session_id": req.session_id,
            }
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return err_resp(f"LLM error: {str(e)}")

    return err_resp("ICARUS is starting up. Please try again in a moment.")

@app.get("/api/v1/health/ready")
async def ready():
    load_tools()
    orch_ok = get_orch() is not None
    llm_ok  = get_llm() is not None
    return {
        "status": "ready",
        "system": "ICARUS",
        "version": "0.1.0",
        "orchestrator": orch_ok,
        "llm": llm_ok,
        "env": os.getenv("ICARUS_ENV", "production"),
    }

logger.info("ICARUS app object created — uvicorn will serve it now")
