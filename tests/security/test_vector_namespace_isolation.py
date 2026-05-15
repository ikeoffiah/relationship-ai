import os
import json
import asyncio
import uuid
import asyncpg
import pytest
from dotenv import load_dotenv

# Load env from root or backend-django
load_dotenv("backend-django/.env.local")
DB_URL = os.environ.get("DATABASE_URL")


@pytest.mark.asyncio
async def test_vector_namespace_isolation():
    """
    Verify that PostgreSQL Row Level Security (RLS) correctly isolates
    vector data between users in the memory_vectors table.

    The test connects as `postgres` (which has BYPASSRLS), then uses
    SET ROLE authenticated to step down to a non-privileged role that
    is subject to RLS — matching the production access pattern.
    """
    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)

    user_id_a = str(uuid.uuid4())
    user_id_b = str(uuid.uuid4())
    memory_id_a = str(uuid.uuid4())
    memory_id_b = str(uuid.uuid4())

    mock_embedding = [0.1] * 1536

    try:
        # ── Setup: insert as postgres (bypasses RLS for setup) ─────
        await conn.execute(
            """
            INSERT INTO users (
                id, username, email, password, first_name, last_name,
                is_superuser, is_staff, is_active, is_minor,
                email_verified, date_joined, created_at
            ) VALUES
                ($1, $2, $3, 'pass', 'Test', 'A', false, false, true, false, false, now(), now()),
                ($4, $5, $6, 'pass', 'Test', 'B', false, false, true, false, false, now(), now())
        """,
            user_id_a,
            f"user_a_{user_id_a[:8]}",
            f"a_{user_id_a[:8]}@test.com",
            user_id_b,
            f"user_b_{user_id_b[:8]}",
            f"b_{user_id_b[:8]}@test.com",
        )

        await conn.execute(
            """
            INSERT INTO user_memories (id, user_id, content, metadata)
            VALUES ($1, $2, 'enc_a', $3), ($4, $5, 'enc_b', $6)
        """,
            memory_id_a,
            user_id_a,
            json.dumps({}),
            memory_id_b,
            user_id_b,
            json.dumps({}),
        )

        await conn.execute(
            """
            INSERT INTO memory_vectors (memory_id, user_id, zone, embedding, metadata)
            VALUES ($1, $2, 'private', $3::vector, $4),
                   ($5, $6, 'private', $7::vector, $8)
        """,
            memory_id_a,
            user_id_a,
            str(mock_embedding),
            json.dumps({"owner": "a"}),
            memory_id_b,
            user_id_b,
            str(mock_embedding),
            json.dumps({"owner": "b"}),
        )

        # ── Switch to authenticated role (subject to RLS) ──────────
        await conn.execute("SET ROLE authenticated")

        # ── Test 1: User A cannot see User B's vector ──────────────
        await conn.execute(f"SET app.current_user_id = '{user_id_a}'")
        rows = await conn.fetch(
            "SELECT * FROM memory_vectors WHERE memory_id = $1", memory_id_b
        )
        assert len(rows) == 0, f"FAIL: User A sees User B's vector ({len(rows)} rows)!"

        # ── Test 2: User A CAN see own vector ──────────────────────
        rows = await conn.fetch(
            "SELECT * FROM memory_vectors WHERE memory_id = $1", memory_id_a
        )
        assert len(rows) == 1, f"FAIL: User A cannot see own vector ({len(rows)} rows)."

        # ── Test 3: User B CAN see own vector ──────────────────────
        await conn.execute(f"SET app.current_user_id = '{user_id_b}'")
        rows = await conn.fetch(
            "SELECT * FROM memory_vectors WHERE memory_id = $1", memory_id_b
        )
        assert len(rows) == 1, f"FAIL: User B cannot see own vector ({len(rows)} rows)."

        # ── Test 4: User B cannot see User A's vector ──────────────
        rows = await conn.fetch(
            "SELECT * FROM memory_vectors WHERE memory_id = $1", memory_id_a
        )
        assert len(rows) == 0, f"FAIL: User B sees User A's vector ({len(rows)} rows)!"

        print("✅ RLS Namespace Isolation Test: ALL 4 ASSERTIONS PASSED")

    finally:
        # ── Cleanup: switch back to postgres for unrestricted deletes
        await conn.execute("RESET ROLE")
        await conn.execute(
            "DELETE FROM memory_vectors WHERE memory_id IN ($1, $2)",
            memory_id_a,
            memory_id_b,
        )
        await conn.execute(
            "DELETE FROM user_memories WHERE id IN ($1, $2)", memory_id_a, memory_id_b
        )
        await conn.execute(
            "DELETE FROM users WHERE id IN ($1, $2)", user_id_a, user_id_b
        )
        await conn.close()


if __name__ == "__main__":
    asyncio.run(test_vector_namespace_isolation())
