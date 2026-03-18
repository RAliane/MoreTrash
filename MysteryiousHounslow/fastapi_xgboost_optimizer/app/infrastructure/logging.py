import logging
import sys
from typing import Dict, Any
import structlog

from app.infrastructure.config import settings


def setup_logging() -> None:
    """Setup structured logging for the application."""
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Configure structlog
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable logging for development
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_request_logger() -> structlog.BoundLogger:
    """Get a logger configured for request context."""
    return structlog.get_logger("request")


def get_optimization_logger() -> structlog.BoundLogger:
    """Get a logger configured for optimization operations."""
    return structlog.get_logger("optimization")


def get_ml_logger() -> structlog.BoundLogger:
    """Get a logger configured for ML operations."""
    return structlog.get_logger("ml")


def get_database_logger() -> structlog.BoundLogger:
    """Get a logger configured for database operations."""
    return structlog.get_logger("database")
