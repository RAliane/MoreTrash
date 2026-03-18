"""Tests for FastMCP tools."""

import pytest

from src.mcp_tools import (
    agent_chat,
    directus_create,
    directus_query,
    memory_add,
    memory_search,
    memory_stats,
)


@pytest.mark.unit
async def test_mcp_directus_query() -> None:
    """Test MCP directus_query tool."""
    # This would need the API to be running
    # For unit tests, we mock or skip
    pass


@pytest.mark.unit
async def test_mcp_directus_create() -> None:
    """Test MCP directus_create tool."""
    pass


@pytest.mark.unit
async def test_mcp_memory_add() -> None:
    """Test MCP memory_add tool."""
    pass


@pytest.mark.unit
async def test_mcp_memory_search() -> None:
    """Test MCP memory_search tool."""
    pass


@pytest.mark.unit
async def test_mcp_agent_chat() -> None:
    """Test MCP agent_chat tool."""
    result = await agent_chat(
        message="Hello, how are you?",
        use_memory=False,
    )

    assert "prompt" in result
    assert "message" in result
    assert result["message"] == "Hello, how are you?"


@pytest.mark.integration
async def test_mcp_end_to_end() -> None:
    """Integration test for MCP tools."""
    # Requires full stack running
    pass
