"""FastMCP tools for the AI agent."""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from src.config import get_settings
from src.directus_client import get_directus_client
from src.logging_config import get_logger
from src.memory import get_memory

logger = get_logger(__name__)

# Initialize FastMCP
mcp = FastMCP("AI Agent MCP")


@mcp.tool()
async def directus_query(
    collection: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Query records from a Directus collection.

    Args:
        collection: Name of the Directus collection
        filters: Optional filters as key-value pairs
        limit: Maximum number of records to return
        offset: Number of records to skip
        sort: List of fields to sort by (prefix with - for descending)

    Returns:
        List of records from the collection
    """
    client = get_directus_client()
    results = await client.query(
        collection=collection,
        filters=filters,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    logger.info(
        "MCP tool: directus_query executed",
        collection=collection,
        results_count=len(results),
    )
    return results


@mcp.tool()
async def directus_create(
    collection: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new record in a Directus collection.

    Args:
        collection: Name of the Directus collection
        data: Record data to create

    Returns:
        Created record with ID
    """
    client = get_directus_client()
    result = await client.create(collection=collection, data=data)
    logger.info(
        "MCP tool: directus_create executed",
        collection=collection,
        record_id=result.get("id"),
    )
    return result


@mcp.tool()
async def directus_update(
    collection: str,
    record_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing record in a Directus collection.

    Args:
        collection: Name of the Directus collection
        record_id: ID of the record to update
        data: Updated record data

    Returns:
        Updated record
    """
    client = get_directus_client()
    result = await client.update(
        collection=collection,
        record_id=record_id,
        data=data,
    )
    logger.info(
        "MCP tool: directus_update executed",
        collection=collection,
        record_id=record_id,
    )
    return result


@mcp.tool()
async def directus_delete(
    collection: str,
    record_id: str,
) -> Dict[str, bool]:
    """
    Delete a record from a Directus collection.

    Args:
        collection: Name of the Directus collection
        record_id: ID of the record to delete

    Returns:
        Success status
    """
    client = get_directus_client()
    success = await client.delete(collection=collection, record_id=record_id)
    logger.info(
        "MCP tool: directus_delete executed",
        collection=collection,
        record_id=record_id,
        success=success,
    )
    return {"success": success}


@mcp.tool()
async def memory_add(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add a memory chunk to the RAG store.

    Args:
        text: Text content to store
        metadata: Optional metadata dictionary

    Returns:
        Stored memory chunk with ID
    """
    memory = get_memory()
    chunk = await memory.add(text=text, metadata=metadata)
    logger.info(
        "MCP tool: memory_add executed",
        chunk_id=chunk.id,
        text_length=len(text),
    )
    return {
        "id": chunk.id,
        "text": chunk.text,
        "metadata": chunk.metadata,
    }


@mcp.tool()
async def memory_search(
    query: str,
    top_k: int = 5,
    threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Search for similar memories in the RAG store.

    Args:
        query: Search query text
        top_k: Number of top results to return
        threshold: Minimum similarity threshold (0-1)

    Returns:
        List of matching memory chunks with similarity scores
    """
    memory = get_memory()
    results = await memory.search(query=query, top_k=top_k, threshold=threshold)
    logger.info(
        "MCP tool: memory_search executed",
        query_length=len(query),
        results_count=len(results),
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in results
    ]


@mcp.tool()
async def memory_get_context(
    query: str,
    max_tokens: int = 2000,
) -> str:
    """
    Get relevant context from memory for a query.

    Args:
        query: Query to find relevant context for
        max_tokens: Maximum tokens to include in context

    Returns:
        Formatted context string for LLM consumption
    """
    memory = get_memory()
    context = await memory.get_context(query=query, max_tokens=max_tokens)
    logger.info(
        "MCP tool: memory_get_context executed",
        query_length=len(query),
        context_length=len(context),
    )
    return context


@mcp.tool()
async def memory_clear() -> Dict[str, int]:
    """
    Clear all memories from the RAG store.

    Returns:
        Count of deleted memory chunks
    """
    memory = get_memory()
    count = await memory.clear()
    logger.info(
        "MCP tool: memory_clear executed",
        deleted_count=count,
    )
    return {"deleted_count": count}


@mcp.tool()
async def memory_stats() -> Dict[str, Any]:
    """
    Get memory store statistics.

    Returns:
        Statistics about the memory store
    """
    memory = get_memory()
    stats = await memory.get_stats()
    logger.info("MCP tool: memory_stats executed")
    return stats


@mcp.tool()
async def agent_chat(
    message: str,
    use_memory: bool = True,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chat with the AI agent, optionally using memory context.

    Args:
        message: User message
        use_memory: Whether to include relevant memory context
        system_prompt: Optional custom system prompt

    Returns:
        Agent response with metadata
    """
    context = ""
    if use_memory:
        memory = get_memory()
        context = await memory.get_context(message)

    # Build prompt with context
    prompt_parts = []
    if system_prompt:
        prompt_parts.append(f"System: {system_prompt}")
    if context:
        prompt_parts.append(f"Relevant context:\n{context}")
    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Assistant:")

    full_prompt = "\n\n".join(prompt_parts)

    # Store the interaction in memory
    memory = get_memory()
    await memory.add(
        text=f"User: {message}",
        metadata={"type": "user_message"},
    )

    logger.info(
        "MCP tool: agent_chat executed",
        message_length=len(message),
        use_memory=use_memory,
        context_length=len(context),
    )

    # Return the constructed prompt for LLM processing
    # In a real implementation, this would call an LLM API
    return {
        "prompt": full_prompt,
        "context_used": bool(context),
        "context_length": len(context),
        "message": message,
    }


def get_mcp() -> FastMCP:
    """Get the FastMCP instance."""
    return mcp
