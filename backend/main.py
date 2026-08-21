import os, sys, logging
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    stream=sys.stdout)
log = logging.getLogger("icarus")
log.info(f"Starting ICARUS on port {os.getenv('PORT', '8000')}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="ICARUS", version="0.1.0")
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/v1/health")
async def health():
    return {"status": "online", "system": "ICARUS", "version": "0.1.0"}

@app.get("/")
async def root():
    return {"status": "online"}

class ChatReq(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "hinglish"
    personality: Optional[str] = "bro"
    history: Optional[list] = []

@app.post("/api/v1/chat")
async def chat(req: ChatReq):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return {"reply": "GEMINI_API_KEY missing from Railway variables.",
                "intent": "error", "used_llm": False, "used_tool": None,
                "tokens_used": 0, "personality": req.personality,
                "language": req.language, "session_id": req.session_id}
    try:
        from google import genai
        client = genai.Client(api_key=key)
        lang_map = {
            "hinglish": "Reply in Hinglish — natural Hindi+English mix. Be casual.",
            "hi": "Reply in Hindi.", "en": "Reply in English.", "mr": "Reply in Marathi."
        }
        system = f"""You are ICARUS, a personal AI Operating System built by Zayd.
Personality: {req.personality}. {lang_map.get(req.language, lang_map['hinglish'])}
Never say 'As an AI'. You are ICARUS."""
        resp = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=f"{system}\n\nUser: {req.message}")
        return {"reply": resp.text, "intent": "conversation",
                "used_llm": True, "used_tool": None, "tokens_used": 0,
                "personality": req.personality, "language": req.language,
                "session_id": req.session_id}
    except Exception as e:
        log.error(f"Gemini error: {e}")
        return {"reply": f"Error: {str(e)}", "intent": "error",
                "used_llm": False, "used_tool": None, "tokens_used": 0,
                "personality": req.personality, "language": req.language,
                "session_id": req.session_id}

log.info("ICARUS app ready")