"""
FastAPI XGBoost Optimizer - Main Application Entry Point

This module initializes and configures the FastAPI application with all
necessary middleware, routers, and configuration for production deployment.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.backend.api.endpoints import router as api_router
from src.backend.api.middleware import LoggingMiddleware, RateLimitMiddleware
from src.backend.middleware.auth import auth0_jwt_bearer
from src.backend.core.config import settings
from src.backend.core.exceptions import (
    ConstraintException,
    DatabaseException,
    OptimizationException,
    ValidationException,
)
from src.backend.database.hasura_client import HasuraClient
from src.backend.database.directus_client import DirectusClient
from src.backend.pipeline import MatchingPipeline
from src.backend.infrastructure.error_handler import ErrorHandler
from src.backend.infrastructure.logging_config import setup_logging
from src.backend.infrastructure.monitoring import setup_monitoring


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    setup_logging()
    setup_monitoring()

    # Initialize Hasura client
    hasura_client = HasuraClient()
    await hasura_client.initialize()
    app.state.hasura_client = hasura_client

    # Initialize Directus client
    directus_client = DirectusClient()
    await directus_client.initialize()
    app.state.directus_client = directus_client

    # Load ML models
    from src.backend.optimization.xgboost_engine import XGBoostEngine

    xgboost_engine = XGBoostEngine()
    await xgboost_engine.load_models()
    app.state.xgboost_engine = xgboost_engine

    yield

    # Shutdown
    await hasura_client.close()
    await directus_client.close()
    await xgboost_engine.cleanup()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="FastAPI XGBoost Optimizer",
        description="Production-ready optimization service with ML and constraint programming",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Add compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Add exception handlers
    error_handler = ErrorHandler()

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request, exc):
        return error_handler.handle_validation_error(exc)

    @app.exception_handler(ConstraintException)
    async def constraint_exception_handler(request, exc):
        return error_handler.handle_constraint_error(exc)

    @app.exception_handler(OptimizationException)
    async def optimization_exception_handler(request, exc):
        return error_handler.handle_optimization_error(exc)

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request, exc):
        return error_handler.handle_database_error(exc)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return _rate_limit_exceeded_handler(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "details": None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        return error_handler.handle_general_error(exc)

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "api": "healthy",
                "hasura": "healthy" if hasattr(app.state, 'hasura_client') and app.state.hasura_client.is_ready else "unhealthy",
                "directus": "healthy" if hasattr(app.state, 'directus_client') and await app.state.directus_client.health_check() else "unhealthy",
                "ml": "healthy" if hasattr(app.state, 'xgboost_engine') and app.state.xgboost_engine.is_ready() else "unhealthy"
            }

    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "name": "FastAPI XGBoost Optimizer",
        "version": "1.0.0",
        "description": "Production-ready optimization service with ML and constraint programming",
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else None,
            "api": "/api/v1",
        },
    }


def main() -> None:
    """Main entry point for running the application."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
