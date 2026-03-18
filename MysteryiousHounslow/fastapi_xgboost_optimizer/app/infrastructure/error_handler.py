from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import traceback
import structlog

from app.infrastructure.logging import get_request_logger

logger = get_request_logger()


class OptimizationException(Exception):
    """Base exception for all optimization errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "OPTIMIZATION_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None,
        cause: str = None,
        context: str = None,
        suggestion: str = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        self.context = context
        self.suggestion = suggestion


class ValidationException(OptimizationException):
    """Input validation errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, error_code="VALIDATION_ERROR", status_code=400, **kwargs
        )


class ConstraintException(OptimizationException):
    """Constraint processing errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, error_code="CONSTRAINT_ERROR", status_code=400, **kwargs
        )


class OptimizationEngineException(OptimizationException):
    """ML/Optimization engine errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="ENGINE_ERROR", status_code=500, **kwargs)


class DatabaseException(OptimizationException):
    """Database operation errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, error_code="DATABASE_ERROR", status_code=500, **kwargs
        )


def create_error_response(
    exception: OptimizationException, request: Request = None
) -> JSONResponse:
    """Create standardized error response."""
    error_response = {
        "error": {
            "code": exception.error_code,
            "message": exception.message,
            "details": exception.details,
        },
        "timestamp": "2026-01-12T10:30:00Z",  # Would use datetime.utcnow() in real implementation
        "request_id": getattr(request, "state", {}).get("request_id", "unknown"),
    }

    if exception.cause:
        error_response["error"]["cause"] = exception.cause
    if exception.context:
        error_response["error"]["context"] = exception.context
    if exception.suggestion:
        error_response["error"]["suggestion"] = exception.suggestion

    # Log the error
    logger.error(
        "Optimization error occurred",
        error_code=exception.error_code,
        message=exception.message,
        status_code=exception.status_code,
        details=exception.details,
        exc_info=True,
    )

    return JSONResponse(status_code=exception.status_code, content=error_response)


def setup_error_handling(app: FastAPI) -> None:
    """Setup global error handling for the FastAPI application."""

    @app.exception_handler(OptimizationException)
    async def optimization_exception_handler(
        request: Request, exc: OptimizationException
    ):
        """Handle custom optimization exceptions."""
        return create_error_response(exc, request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        error_response = {
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": {"status_code": exc.status_code},
            },
            "timestamp": "2026-01-12T10:30:00Z",
            "request_id": getattr(request, "state", {}).get("request_id", "unknown"),
        }

        logger.warning(
            "HTTP exception occurred", status_code=exc.status_code, detail=exc.detail
        )

        return JSONResponse(status_code=exc.status_code, content=error_response)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        error_response = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__},
            },
            "timestamp": "2026-01-12T10:30:00Z",
            "request_id": getattr(request, "state", {}).get("request_id", "unknown"),
        }

        logger.error(
            "Unexpected error occurred",
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )

        return JSONResponse(status_code=500, content=error_response)
