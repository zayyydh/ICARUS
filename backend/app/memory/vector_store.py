"""
ICARUS Vector Store
====================
Semantic memory backed by Qdrant.
Stores conversation summaries and documents as vectors.
Enables "what did I say about X?" type queries.

Uses all-MiniLM-L6-v2 for local embeddings — no API cost.

Usage:
    from app.memory.vector_store import vector_store
    await vector_store.upsert("session-123", "Zayd asked about recursion", {"type": "conversation"})
    results = await vector_store.search("recursion questions")
"""

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Any

from app.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION    = settings.QDRANT_COLLECTION
VECTOR_SIZE   = 384   # all-MiniLM-L6-v2 output dimension
TOP_K         = settings.TOP_K_RESULTS


class VectorStore:
    """
    Qdrant-backed semantic memory.
    Gracefully degrades to no-op if Qdrant or
    sentence-transformers aren't available.
    """

    def __init__(self):
        self._client    = None
        self._embedder  = None
        self._ready     = False
        logger.info("Vector store initialized (lazy connection)")

    async def _ensure_ready(self) -> bool:
        """
        Lazy initialization — connects to Qdrant and loads
        embedding model on first use.
        """
        if self._ready:
            return True

        try:
            # Load embedding model
            from sentence_transformers import SentenceTransformer
            loop = asyncio.get_event_loop()
            self._embedder = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(settings.EMBEDDING_MODEL)
            )
            logger.info(
                "Embedding model loaded",
                extra={"model": settings.EMBEDDING_MODEL}
            )
        except Exception as e:
            logger.warning(
                "sentence-transformers unavailable",
                extra={"error": str(e)}
            )
            return False

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import (
                Distance, VectorParams, PointStruct
            )
            self._client = QdrantClient(url=settings.QDRANT_URL)

            # Create collection if it doesn't exist
            existing = [c.name for c in self._client.get_collections().collections]
            if COLLECTION not in existing:
                self._client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE,
                    )
                )
                logger.info(
                    "Qdrant collection created",
                    extra={"collection": COLLECTION}
                )
            self._ready = True
            logger.info(
                "Vector store ready",
                extra={"url": settings.QDRANT_URL, "collection": COLLECTION}
            )
            return True

        except Exception as e:
            logger.warning(
                "Qdrant unavailable — vector memory disabled",
                extra={"error": str(e)}
            )
            self._client = None
            return False

    async def _embed(self, text: str) -> list[float]:
        """Convert text to embedding vector."""
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None,
            lambda: self._embedder.encode(text).tolist()
        )
        return vector

    # ── Public API ────────────────────────────────────────────────

    async def upsert(
        self,
        doc_id:   str,
        text:     str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a text chunk with its vector embedding.

        Args:
            doc_id:   Unique identifier for this chunk
            text:     The text to embed and store
            metadata: Extra data stored alongside the vector
                      e.g. {"type": "conversation", "session": "abc"}

        Returns True if stored successfully.
        """
        if not await self._ensure_ready():
            return False

        try:
            from qdrant_client.models import PointStruct

            vector = await self._embed(text)
            payload = {
                "text":      text,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.upsert(
                    collection_name=COLLECTION,
                    points=[PointStruct(
                        id=self._to_uuid(doc_id),
                        vector=vector,
                        payload=payload,
                    )]
                )
            )

            logger.debug(
                "Vector stored",
                extra={"doc_id": doc_id, "chars": len(text)}
            )
            return True

        except Exception as e:
            logger.error(
                "Vector upsert failed",
                extra={"error": str(e)}
            )
            return False

    async def search(
        self,
        query:  str,
        top_k:  int = TOP_K,
        filter: dict | None = None,
    ) -> list[dict]:
        """
        Search for semantically similar chunks.

        Args:
            query:  Natural language search query
            top_k:  Number of results to return
            filter: Optional Qdrant filter dict

        Returns list of {text, score, metadata} dicts.
        """
        if not await self._ensure_ready():
            return []

        try:
            from qdrant_client.models import Filter

            vector = await self._embed(query)

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._client.search(
                    collection_name=COLLECTION,
                    query_vector=vector,
                    limit=top_k,
                    with_payload=True,
                )
            )

            return [
                {
                    "text":      hit.payload.get("text", ""),
                    "score":     round(hit.score, 4),
                    "metadata":  {
                        k: v for k, v in hit.payload.items()
                        if k not in ("text", "timestamp")
                    },
                    "timestamp": hit.payload.get("timestamp", ""),
                }
                for hit in results
                if hit.score > 0.4   # Relevance threshold
            ]

        except Exception as e:
            logger.error(
                "Vector search failed",
                extra={"error": str(e)}
            )
            return []

    async def store_conversation_turn(
        self,
        session_id: str,
        user_msg:   str,
        icarus_msg: str,
    ) -> None:
        """
        Store a conversation exchange in vector memory.
        Called after every completed exchange.
        Enables "what did I ask about last week?" queries.
        """
        text = f"User: {user_msg}\nICARUS: {icarus_msg}"
        doc_id = f"conv_{session_id}_{uuid.uuid4().hex[:8]}"
        await self.upsert(
            doc_id=doc_id,
            text=text,
            metadata={
                "type":       "conversation",
                "session_id": session_id,
            }
        )

    async def recall_relevant(self, query: str) -> str:
        """
        Search vector memory and return formatted context string.
        Injected into LLM prompt for memory-grounded responses.
        """
        results = await self.search(query, top_k=3)
        if not results:
            return ""

        lines = ["[Relevant past context]"]
        for r in results:
            lines.append(f"- {r['text'][:200]}  (relevance: {r['score']})")

        return "\n".join(lines)

    def _to_uuid(self, id_str: str) -> str:
        """Convert any string to a valid UUID for Qdrant."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, id_str))


# ── Singleton ──────────────────────────────────────────────────────
vector_store = VectorStore()