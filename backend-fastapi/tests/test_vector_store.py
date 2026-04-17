import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.vector_store import VectorMemoryStore


@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock()
    return client


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    pool.acquire = MagicMock()

    conn = AsyncMock()
    # Mock context manager for pool.acquire()
    pool.acquire.return_value.__aenter__.return_value = conn

    return pool, conn


@pytest.mark.asyncio
async def test_vector_store_upsert(mock_openai_client, mock_pool):
    pool, conn = mock_pool

    # Use AsyncMock for create_pool since it is awaited
    with (
        patch("app.memory.vector_store.AsyncOpenAI", return_value=mock_openai_client),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
    ):
        mock_create_pool.return_value = pool
        store = VectorMemoryStore(db_url="mock_url")

        # Mock embedding response
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2])]
        )

        user_id = "user123"
        memory_id = "mem123"
        text = "hello world"
        metadata = {"foo": "bar"}

        result = await store.upsert(user_id, memory_id, text, metadata)

        assert result == memory_id

        # Verify RLS context was set
        conn.execute.assert_any_call("SET ROLE authenticated")
        conn.execute.assert_any_call(f"SET app.current_user_id = '{user_id}'")

        # Verify insert call
        # Check that one of the execute calls contains the INSERT string
        insert_call_found = False
        for call in conn.execute.call_args_list:
            if "INSERT INTO memory_vectors" in str(call):
                insert_call_found = True
                break
        assert insert_call_found, "INSERT INTO memory_vectors not called"

        # Verify role reset
        conn.execute.assert_any_call("RESET ROLE")


@pytest.mark.asyncio
async def test_vector_store_query(mock_openai_client, mock_pool):
    pool, conn = mock_pool

    with (
        patch("app.memory.vector_store.AsyncOpenAI", return_value=mock_openai_client),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
    ):
        mock_create_pool.return_value = pool
        store = VectorMemoryStore(db_url="mock_url")

        # Mock embedding response
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2])]
        )

        # Mock fetch result
        conn.fetch.return_value = [
            {"memory_id": "mem1", "metadata": {"a": 1}, "similarity": 0.95},
            {"memory_id": "mem2", "metadata": {"b": 2}, "similarity": 0.85},
        ]

        results = await store.query("user123", "test query", top_k=2)

        assert len(results) == 2
        assert results[0].memory_id == "mem1"
        assert results[0].similarity == 0.95

        # Verify RLS context
        conn.execute.assert_any_call("SET ROLE authenticated")

        # Verify query call
        conn.fetch.assert_called_once()
        args = conn.fetch.call_args[0]
        # embedding is stringified in the call
        assert "[0.1, 0.2]" in str(args)


@pytest.mark.asyncio
async def test_vector_store_delete(mock_openai_client, mock_pool):
    pool, conn = mock_pool

    with (
        patch("app.memory.vector_store.AsyncOpenAI", return_value=mock_openai_client),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
    ):
        mock_create_pool.return_value = pool
        store = VectorMemoryStore(db_url="mock_url")
        conn.execute.return_value = "DELETE 1"

        success = await store.delete("user123", "mem123")
        assert success is True

        conn.execute.return_value = "DELETE 0"
        success = await store.delete("user123", "mem123")
        assert success is False


@pytest.mark.asyncio
async def test_vector_store_delete_namespace(mock_openai_client, mock_pool):
    pool, conn = mock_pool

    with (
        patch("app.memory.vector_store.AsyncOpenAI", return_value=mock_openai_client),
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
    ):
        mock_create_pool.return_value = pool
        store = VectorMemoryStore(db_url="mock_url")
        conn.execute.return_value = "DELETE 5"

        count = await store.delete_namespace("user123")
        assert count == 5
