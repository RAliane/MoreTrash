"""FastAPI main application with FastMCP integration."""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import orjson
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from src.config import get_settings
from src.database.spatial_factory import (
    close_spatial_backend,
    init_spatial_backend,
)
from src.directus_client import get_directus_client, init_directus
from src.logging_config import configure_logging, get_logger
from src.memory import get_memory, init_memory
from src.memory_graph import close_graph_memory, init_graph_memory
from src.mcp_tools import get_mcp

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
ACTIVE_CONNECTIONS = Counter(
    "active_connections",
    "Number of active connections",
)


def custom_json_response(data: Any) -> JSONResponse:
    """Create JSON response with orjson for performance."""
    return JSONResponse(
        content=data,
        media_type="application/json",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up AI Agent application...")
    
    settings = get_settings()

    # Initialize Directus
    await init_directus()
    logger.info("Directus initialized")

    # Initialize Memory (SQLite-based)
    await init_memory()
    logger.info("Memory system initialized")
    
    # Initialize Graph Memory (Neo4j-backed) if enabled
    if settings.use_graph_memory:
        await init_graph_memory()
        logger.info("Graph memory initialized")
    
    # Initialize Spatial Backend if enabled
    if settings.use_neo4j_spatial:
        await init_spatial_backend()
        logger.info("Spatial backend initialized")

    # Log configuration
    logger.info(
        "Application configuration loaded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        graph_mode=settings.is_graph_mode,
        spatial_backend="Neo4j" if settings.use_neo4j_spatial else "None",
    )

    yield

    # Shutdown
    logger.info("Shutting down AI Agent application...")
    
    # Close Spatial Backend if initialized
    if settings.use_neo4j_spatial:
        await close_spatial_backend()
        logger.info("Spatial backend closed")
    
    # Close Graph Memory if initialized
    if settings.use_graph_memory:
        await close_graph_memory()
        logger.info("Graph memory closed")

    # Close Directus client
    client = get_directus_client()
    await client.close()
    logger.info("Directus client closed")

    logger.info("Application shutdown complete")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="End-to-end AI agent system with Directus, FastAPI, FastMCP, and Cognee RAG",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect Prometheus metrics."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

    return response


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs" if settings.is_development else None,
        "health": "/health",
        "metrics": settings.metrics_endpoint,
        "agent": settings.fastmcp_agent_endpoint,
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    memory = get_memory()
    memory_stats = await memory.get_stats()
    
    # Build services status
    services = {
        "directus": "connected",
        "memory": {
            "status": "ready",
            "chunks": memory_stats["total_chunks"],
        },
    }
    
    # Add Neo4j/Graph status if enabled
    if settings.use_neo4j_spatial:
        try:
            from src.database.spatial_factory import get_spatial_backend
            backend = await get_spatial_backend()
            services["spatial_backend"] = {
                "status": "healthy" if await backend.health_check() else "unhealthy",
                "type": "Neo4j",
            }
        except Exception as exc:
            logger.debug("Spatial backend health check failed", exc_info=True)
            services["spatial_backend"] = {
                "status": "error",
                "error": str(exc),
            }
    
    if settings.use_graph_memory:
        services["graph_memory"] = {
            "status": "enabled",
            "mode": "Neo4j-backed" if settings.is_graph_mode else "fallback",
        }

    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "graph_mode": settings.is_graph_mode,
        "services": services,
    }


@app.get(settings.metrics_endpoint)
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Directus API routes
@app.get("/api/collections/{collection}")
async def list_records(
    collection: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List records from a Directus collection."""
    client = get_directus_client()
    results = await client.query(collection=collection, limit=limit, offset=offset)
    return results


@app.post("/api/collections/{collection}")
async def create_record(
    collection: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a record in a Directus collection."""
    client = get_directus_client()
    result = await client.create(collection=collection, data=data)
    return result


@app.get("/api/collections/{collection}/{record_id}")
async def get_record(
    collection: str,
    record_id: str,
) -> Optional[Dict[str, Any]]:
    """Get a single record by ID."""
    client = get_directus_client()
    result = await client.get_by_id(collection=collection, record_id=record_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return result


@app.patch("/api/collections/{collection}/{record_id}")
async def update_record(
    collection: str,
    record_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a record in a Directus collection."""
    client = get_directus_client()
    result = await client.update(
        collection=collection,
        record_id=record_id,
        data=data,
    )
    return result


@app.delete("/api/collections/{collection}/{record_id}")
async def delete_record(
    collection: str,
    record_id: str,
) -> Dict[str, bool]:
    """Delete a record from a Directus collection."""
    client = get_directus_client()
    success = await client.delete(collection=collection, record_id=record_id)
    return {"success": success}


# Memory API routes
@app.post("/api/memory")
async def add_memory(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add a memory chunk."""
    memory = get_memory()
    chunk = await memory.add(text=text, metadata=metadata)
    return {
        "id": chunk.id,
        "text": chunk.text,
        "metadata": chunk.metadata,
    }


@app.get("/api/memory/search")
async def search_memory(
    query: str,
    top_k: int = 5,
    threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Search memory chunks."""
    memory = get_memory()
    results = await memory.search(query=query, top_k=top_k, threshold=threshold)
    return [
        {
            "id": r.id,
            "text": r.text,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in results
    ]


@app.get("/api/memory/context")
async def get_memory_context(
    query: str,
    max_tokens: int = 2000,
) -> Dict[str, str]:
    """Get relevant context from memory."""
    memory = get_memory()
    context = await memory.get_context(query=query, max_tokens=max_tokens)
    return {"context": context}


@app.get("/api/memory/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics."""
    memory = get_memory()
    stats = await memory.get_stats()
    return stats


@app.delete("/api/memory")
async def clear_memory() -> Dict[str, int]:
    """Clear all memories."""
    memory = get_memory()
    count = await memory.clear()
    return {"deleted_count": count}


# Agent chat endpoint
@app.post("/api/chat")
async def chat(
    message: str,
    use_memory: bool = True,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Chat with the AI agent."""
    from src.mcp_tools import agent_chat
    result = await agent_chat(
        message=message,
        use_memory=use_memory,
        system_prompt=system_prompt,
    )
    return result


# Mount FastMCP
mcp = get_mcp()
app.mount(settings.fastmcp_agent_endpoint, mcp)


def main():
    """Main entry point for the application."""
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        workers=settings.fastapi_workers,
        reload=settings.fastapi_reload and settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
