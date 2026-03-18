"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import Settings, get_settings
from src.directus_client import DirectusClient
from src.main import app
from src.memory import CogneeMemory


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_env="testing",
        debug=True,
        log_level="DEBUG",
        directus_database_path="artifacts/test_data.db",
        cognee_vector_store="artifacts/test_embeddings.db",
    )


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def directus_client(test_settings: Settings) -> AsyncGenerator[DirectusClient, None]:
    """Create Directus client for testing."""
    client = DirectusClient(
        database_path=test_settings.directus_database_path,
    )
    await client.bootstrap_collections()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def memory(test_settings: Settings) -> AsyncGenerator[CogneeMemory, None]:
    """Create memory instance for testing."""
    memory = CogneeMemory(
        vector_store_path=test_settings.cognee_vector_store,
    )
    memory._ensure_schema()
    yield memory
    # Cleanup
    await memory.clear()


@pytest.fixture(autouse=True)
def reset_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset singleton dependencies between tests."""
    import src.directus_client
    import src.memory

    monkeypatch.setattr(src.directus_client, "_directus_client", None)
    monkeypatch.setattr(src.memory, "_memory_instance", None)
