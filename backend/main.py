"""
ICARUS — Entry point
"""
from fastapi import FastAPI
from app.api.v1 import chat, voice, health

app = FastAPI(
    title="Project ICARUS",
    description="AI Operating System",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router,   prefix="/api/v1")
app.include_router(voice.router,  prefix="/api/v1")
