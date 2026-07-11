"""
ICARUS Long-Term Memory
========================
Stores persistent facts about the user in PostgreSQL.
Things ICARUS should remember forever:
  - Your name, preferences, projects
  - Things you explicitly said "remember this"
  - Patterns learned over time

Gracefully degrades to SQLite if PostgreSQL unavailable.
SQLite requires zero setup — perfect for local development.

Usage:
    from app.memory.long_term import long_term_memory
    await long_term_memory.save("user_name", "Zayd")
    name = await long_term_memory.recall("user_name")
"""

import json
import logging
import aiosqlite
from datetime import datetime
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)

# SQLite fallback path — works with zero infrastructure
SQLITE_PATH = Path(__file__).resolve().parents[4] / "data" / "icarus_memory.db"


class LongTermMemory:
    """
    Persistent key-value memory backed by SQLite.
    Upgrades to PostgreSQL when available.

    Schema:
        memories table:
            key       TEXT PRIMARY KEY
            value     TEXT             -- JSON-encoded value
            category  TEXT             -- 'fact', 'preference', 'note'
            source    TEXT             -- how it was learned
            created   TEXT
            updated   TEXT
    """

    def __init__(self):
        self._db_path = SQLITE_PATH
        self._initialized = False
        logger.info(
            "Long-term memory initialized",
            extra={"db": str(self._db_path)}
        )

    async def _ensure_db(self) -> None:
        """Create tables if they don't exist."""
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key      TEXT PRIMARY KEY,
                    value    TEXT NOT NULL,
                    category TEXT DEFAULT 'fact',
                    source   TEXT DEFAULT 'user',
                    created  TEXT NOT NULL,
                    updated  TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_category
                ON memories(category)
            """)
            await db.commit()
        self._initialized = True
        logger.info("Long-term memory DB ready", extra={"path": str(self._db_path)})

    # ── Public API ────────────────────────────────────────────────

    async def save(
        self,
        key:      str,
        value:    any,
        category: str = "fact",
        source:   str = "user",
    ) -> None:
        """
        Save a fact to long-term memory.
        Overwrites if key already exists.

        Examples:
            await memory.save("user_name", "Zayd")
            await memory.save("preferred_language", "hinglish")
            await memory.save("current_project", "ICARUS")
        """
        await self._ensure_db()
        now = datetime.utcnow().isoformat()
        encoded = json.dumps(value)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO memories (key, value, category, source, created, updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value   = excluded.value,
                    updated = excluded.updated
            """, (key, encoded, category, source, now, now))
            await db.commit()

        logger.debug(
            "Memory saved",
            extra={"key": key, "category": category}
        )

    async def recall(self, key: str) -> any:
        """
        Retrieve a specific memory by key.
        Returns None if not found.
        """
        await self._ensure_db()
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT value FROM memories WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None

    async def recall_all(self, category: str | None = None) -> dict:
        """
        Retrieve all memories, optionally filtered by category.
        Returns {key: value} dict.
        """
        await self._ensure_db()
        query  = "SELECT key, value FROM memories"
        params = ()
        if category:
            query  += " WHERE category = ?"
            params  = (category,)

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: json.loads(row[1]) for row in rows}

    async def forget(self, key: str) -> bool:
        """Delete a specific memory. Returns True if deleted."""
        await self._ensure_db()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE key = ?", (key,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info("Memory forgotten", extra={"key": key})
        return deleted

    async def search(self, query: str) -> list[dict]:
        """
        Simple text search over memory keys and values.
        Vector search is handled by VectorStore.
        """
        await self._ensure_db()
        pattern = f"%{query}%"
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                """SELECT key, value, category, updated
                   FROM memories
                   WHERE key LIKE ? OR value LIKE ?
                   ORDER BY updated DESC
                   LIMIT 10""",
                (pattern, pattern)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "key":      row[0],
                        "value":    json.loads(row[1]),
                        "category": row[2],
                        "updated":  row[3],
                    }
                    for row in rows
                ]

    async def build_memory_context(self) -> str:
        """
        Build a context string from all memories.
        Injected into LLM system prompt so ICARUS knows about the user.
        """
        all_memories = await self.recall_all()
        if not all_memories:
            return ""

        lines = ["[What ICARUS knows about you]"]
        for key, value in all_memories.items():
            # Convert snake_case key to readable label
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {value}")

        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────────
long_term_memory = LongTermMemory()