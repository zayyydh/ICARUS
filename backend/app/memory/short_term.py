"""
ICARUS Short-Term Memory
=========================
Stores the current conversation history in Redis.
Fast, temporary — expires after session inactivity.

Each session gets a unique ID.
History is a list of {role, content} dicts stored as JSON.

Usage:
    from app.memory.short_term import short_term_memory
    await short_term_memory.add(session_id, "user", "gana baja")
    history = await short_term_memory.get(session_id)
"""

import json
import logging
from datetime import timedelta

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Session expires after 2 hours of inactivity
SESSION_TTL = timedelta(hours=2)
MAX_TURNS   = settings.MAX_HISTORY_TURNS


class ShortTermMemory:
    """
    Redis-backed conversation history.
    Gracefully degrades to in-memory dict if Redis unavailable.
    """

    def __init__(self):
        self._redis  = None
        self._local: dict[str, list[dict]] = {}   # fallback
        self._use_redis = False
        logger.info("Short-term memory initialized (lazy Redis connection)")

    async def _get_redis(self):
        """Lazy Redis connection — only connects when first used."""
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._use_redis = True
            logger.info(
                "Redis connected",
                extra={"url": settings.REDIS_URL}
            )
        except Exception as e:
            logger.warning(
                "Redis unavailable — using in-memory fallback",
                extra={"error": str(e)}
            )
            self._redis = None
        return self._redis

    def _session_key(self, session_id: str) -> str:
        return f"icarus:session:{session_id}:history"

    # ── Public API ────────────────────────────────────────────────

    async def add(
        self,
        session_id: str,
        role:       str,
        content:    str,
    ) -> None:
        """Add a message to session history."""
        message = {"role": role, "content": content}

        redis = await self._get_redis()

        if redis and self._use_redis:
            try:
                key = self._session_key(session_id)
                # Append to Redis list
                await redis.rpush(key, json.dumps(message))
                # Reset TTL on every new message
                await redis.expire(key, int(SESSION_TTL.total_seconds()))
                # Trim to max turns (each turn = 2 messages)
                length = await redis.llen(key)
                if length > MAX_TURNS * 2:
                    await redis.ltrim(key, -MAX_TURNS * 2, -1)
                return
            except Exception as e:
                logger.warning(
                    "Redis write failed — using local fallback",
                    extra={"error": str(e)}
                )

        # In-memory fallback
        if session_id not in self._local:
            self._local[session_id] = []
        self._local[session_id].append(message)
        # Trim
        if len(self._local[session_id]) > MAX_TURNS * 2:
            self._local[session_id] = self._local[session_id][-MAX_TURNS * 2:]

    async def get(self, session_id: str) -> list[dict]:
        """Get full conversation history for a session."""
        redis = await self._get_redis()

        if redis and self._use_redis:
            try:
                key      = self._session_key(session_id)
                raw_msgs = await redis.lrange(key, 0, -1)
                return [json.loads(m) for m in raw_msgs]
            except Exception as e:
                logger.warning(
                    "Redis read failed",
                    extra={"error": str(e)}
                )

        return self._local.get(session_id, [])

    async def clear(self, session_id: str) -> None:
        """Clear history for a session."""
        redis = await self._get_redis()
        if redis and self._use_redis:
            try:
                await redis.delete(self._session_key(session_id))
                return
            except Exception:
                pass
        self._local.pop(session_id, None)

    async def get_recent(
        self,
        session_id: str,
        turns:      int = 5,
    ) -> list[dict]:
        """Get only the most recent N turns."""
        history = await self.get(session_id)
        return history[-(turns * 2):]


# ── Singleton ──────────────────────────────────────────────────────
short_term_memory = ShortTermMemory()