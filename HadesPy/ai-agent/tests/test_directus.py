"""Tests for Directus client."""

import pytest

from src.directus_client import DirectusClient


@pytest.mark.unit
async def test_directus_create_and_query(directus_client: DirectusClient) -> None:
    """Test creating and querying records."""
    # Create a test record
    data = {"role": "user", "content": "Test message", "metadata": {"test": True}}
    created = await directus_client.create("messages", data)

    assert "id" in created
    assert created["role"] == "user"
    assert created["content"] == "Test message"

    # Query the record
    results = await directus_client.query("messages", filters={"role": "user"})
    assert len(results) >= 1


@pytest.mark.unit
async def test_directus_update(directus_client: DirectusClient) -> None:
    """Test updating records."""
    # Create record
    created = await directus_client.create("messages", {"role": "user", "content": "Original"})
    record_id = created["id"]

    # Update record
    updated = await directus_client.update("messages", record_id, {"content": "Updated"})
    assert updated["content"] == "Updated"


@pytest.mark.unit
async def test_directus_delete(directus_client: DirectusClient) -> None:
    """Test deleting records."""
    # Create record
    created = await directus_client.create("messages", {"role": "user", "content": "To delete"})
    record_id = created["id"]

    # Delete record
    success = await directus_client.delete("messages", record_id)
    assert success is True

    # Verify deletion
    result = await directus_client.get_by_id("messages", record_id)
    assert result is None


@pytest.mark.unit
async def test_directus_get_by_id(directus_client: DirectusClient) -> None:
    """Test getting record by ID."""
    # Create record
    created = await directus_client.create("messages", {"role": "user", "content": "By ID"})
    record_id = created["id"]

    # Get by ID
    result = await directus_client.get_by_id("messages", record_id)
    assert result is not None
    assert result["id"] == record_id
    assert result["content"] == "By ID"
