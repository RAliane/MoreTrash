"""Factory for spatial backend selection.

Provides a clean interface for getting the configured spatial backend
based on feature flags and environment settings.
"""

from typing import Optional

from src.config import get_settings
from src.core.spatial_interface import SpatialBackend
from src.logging_config import get_logger

logger = get_logger(__name__)

# Singleton instance cache
_backend_instance: Optional[SpatialBackend] = None


async def get_spatial_backend() -> SpatialBackend:
    """Get configured spatial backend singleton.
    
    Returns the appropriate backend based on feature flags:
    - USE_NEO4J_SPATIAL=True → Neo4jSpatialBackend
    - Default → raises RuntimeError (no fallback after migration)
    
    Returns:
        Configured SpatialBackend instance
    
    Raises:
        RuntimeError: If no backend is configured
    """
    global _backend_instance
    
    if _backend_instance is not None:
        return _backend_instance
    
    settings = get_settings()
    
    if settings.use_neo4j_spatial:
        from src.database.neo4j_spatial import Neo4jSpatialBackend
        
        _backend_instance = Neo4jSpatialBackend(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        logger.info(
            "Spatial backend initialized",
            backend="Neo4jSpatialBackend",
            uri=settings.neo4j_uri,
        )
        return _backend_instance
    
    raise RuntimeError(
        "No spatial backend configured. "
        "Set USE_NEO4J_SPATIAL=true in environment."
    )


def reset_backend() -> None:
    """Reset the backend singleton (for testing).
    
    Call this in test teardown to ensure clean state.
    """
    global _backend_instance
    _backend_instance = None
    logger.debug("Spatial backend reset")


async def init_spatial_backend() -> None:
    """Initialize the spatial backend on application startup.
    
    This should be called during FastAPI lifespan startup.
    """
    backend = await get_spatial_backend()
    await backend.initialize()
    logger.info("Spatial backend ready")


async def close_spatial_backend() -> None:
    """Close the spatial backend on application shutdown.
    
    This should be called during FastAPI lifespan shutdown.
    """
    global _backend_instance
    
    if _backend_instance is not None:
        await _backend_instance.close()
        _backend_instance = None
        logger.info("Spatial backend closed")
