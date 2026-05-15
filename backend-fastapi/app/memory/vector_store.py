import os
import json
import asyncpg
from dataclasses import dataclass
from typing import List, Dict
from openai import AsyncOpenAI


@dataclass
class MemoryRecord:
    memory_id: str
    metadata: dict
    similarity: float


class NamespaceAccessDenied(Exception):
    pass


class VectorMemoryStore:
    """
    MVP implementation using pgvector on Supabase.
    Namespace isolation enforced via PostgreSQL RLS.

    Important: The Supabase pooler connects as `postgres` which has
    BYPASSRLS. We use `SET ROLE authenticated` to step down to a
    non-privileged role so RLS policies are enforced.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    async def _get_pool(self) -> asyncpg.Pool:
        if not hasattr(self, "_pool"):
            self._pool = await asyncpg.create_pool(self.db_url, statement_cache_size=0)
        return self._pool

    async def _set_rls_context(self, conn, user_id: str):
        """Step down to authenticated role and set user context for RLS."""
        await conn.execute("SET ROLE authenticated")
        await conn.execute(f"SET app.current_user_id = '{user_id}'")

    async def _reset_role(self, conn):
        """Reset back to the connection's original role."""
        await conn.execute("RESET ROLE")

    async def _embed(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(input=[text], model=self.model)
        return response.data[0].embedding

    async def upsert(
        self,
        user_id: str,
        memory_id: str,
        text: str,
        metadata: Dict,
        zone: str = "private",
    ) -> str:
        embedding = await self._embed(text)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await self._set_rls_context(conn, user_id)
            try:
                await conn.execute(
                    """
                    INSERT INTO memory_vectors (memory_id, user_id, zone, embedding, metadata)
                    VALUES ($1, $2, $3, $4::vector, $5)
                    ON CONFLICT (memory_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata
                """,
                    memory_id,
                    user_id,
                    zone,
                    str(embedding),
                    json.dumps(metadata),
                )
            finally:
                await self._reset_role(conn)
        return memory_id

    async def query(
        self, user_id: str, query_text: str, top_k: int = 5, zone: str = "private"
    ) -> List[MemoryRecord]:
        embedding = await self._embed(query_text)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await self._set_rls_context(conn, user_id)
            try:
                rows = await conn.fetch(
                    """
                    SELECT memory_id, metadata,
                           1 - (embedding <=> $1::vector) AS similarity
                    FROM memory_vectors
                    WHERE zone = $2
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                """,
                    str(embedding),
                    zone,
                    top_k,
                )
            finally:
                await self._reset_role(conn)

        return [
            MemoryRecord(
                memory_id=str(r["memory_id"]),
                metadata=r["metadata"],
                similarity=float(r["similarity"]),
            )
            for r in rows
        ]

    async def delete(self, user_id: str, memory_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await self._set_rls_context(conn, user_id)
            try:
                result = await conn.execute(
                    "DELETE FROM memory_vectors WHERE memory_id = $1", memory_id
                )
            finally:
                await self._reset_role(conn)
        return result != "DELETE 0"

    async def delete_namespace(self, user_id: str) -> int:
        """Used for GDPR erasure — deletes all vectors for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await self._set_rls_context(conn, user_id)
            try:
                result = await conn.execute(
                    "DELETE FROM memory_vectors WHERE user_id = $1", user_id
                )
            finally:
                await self._reset_role(conn)
        # result is e.g., "DELETE 5"
        count = int(result.split()[-1])
        return count
