"""Tests for Cognee memory system."""

import pytest

from src.memory import CogneeMemory


@pytest.mark.unit
async def test_memory_add(memory: CogneeMemory) -> None:
    """Test adding memory chunks."""
    chunk = await memory.add(
        text="This is a test memory",
        metadata={"type": "test"},
    )

    assert chunk.id is not None
    assert chunk.text == "This is a test memory"
    assert chunk.metadata == {"type": "test"}
    assert chunk.embedding is not None


@pytest.mark.unit
async def test_memory_search(memory: CogneeMemory) -> None:
    """Test searching memories."""
    # Add test memories
    await memory.add(text="Python is a programming language", metadata={"topic": "programming"})
    await memory.add(text="Machine learning is fascinating", metadata={"topic": "ai"})
    await memory.add(text="FastAPI is a modern web framework", metadata={"topic": "programming"})

    # Search
    results = await memory.search("programming languages", top_k=2)

    assert len(results) > 0
    # First result should be about Python
    assert "Python" in results[0].text or "FastAPI" in results[0].text


@pytest.mark.unit
async def test_memory_get_context(memory: CogneeMemory) -> None:
    """Test getting context for queries."""
    # Add relevant memories
    await memory.add(text="FastAPI is built on Starlette and Pydantic")
    await memory.add(text="Pydantic provides data validation")

    # Get context
    context = await memory.get_context("Tell me about FastAPI", max_tokens=500)

    assert len(context) > 0
    assert "FastAPI" in context


@pytest.mark.unit
async def test_memory_batch_add(memory: CogneeMemory) -> None:
    """Test batch adding memories."""
    texts = [
        "First test memory",
        "Second test memory",
        "Third test memory",
    ]
    metadatas = [{"index": i} for i in range(len(texts))]

    chunks = await memory.add_batch(texts, metadatas)

    assert len(chunks) == 3
    for i, chunk in enumerate(chunks):
        assert chunk.id is not None
        assert chunk.text == texts[i]
        assert chunk.metadata == {"index": i}


@pytest.mark.unit
async def test_memory_stats(memory: CogneeMemory) -> None:
    """Test memory statistics."""
    # Add some memories
    await memory.add(text="Test memory 1")
    await memory.add(text="Test memory 2")

    stats = await memory.get_stats()

    assert "total_chunks" in stats
    assert stats["total_chunks"] >= 2
    assert "embedding_model" in stats
    assert "embedding_dimension" in stats


@pytest.mark.unit
async def test_memory_clear(memory: CogneeMemory) -> None:
    """Test clearing all memories."""
    # Add memories
    await memory.add(text="Memory to clear")
    await memory.add(text="Another memory")

    # Clear
    count = await memory.clear()
    assert count >= 2

    # Verify cleared
    stats = await memory.get_stats()
    assert stats["total_chunks"] == 0
