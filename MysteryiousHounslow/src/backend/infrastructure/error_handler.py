"""
Global error handler for the FastAPI XGBoost Optimizer.

This module provides centralized error handling with detailed context,
cause analysis, and corrective suggestions for all application errors.
"""

import traceback
from typing import Any, Dict, Optional, Type

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from src.backend.core.config import settings
from src.backend.core.exceptions import (
    AuthenticationException,
    BaseOptimizerException,
    ConstraintException,
    DatabaseException,
    OptimizationException,
    RateLimitException,
    ValidationException,
    WorkflowException,
)
from src.backend.infrastructure.logging_config import get_logger


class ErrorHandler:
    """
    Global error handler for the application.
    
    Provides consistent error handling with detailed context,
    cause analysis, and corrective suggestions.
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = get_logger(__name__)
        
        # Error mapping for different exception types
        self.error_handlers = {
            ValidationException: self.handle_validation_error,
            ConstraintException: self.handle_constraint_error,
            OptimizationException: self.handle_optimization_error,
            DatabaseException: self.handle_database_error,
            WorkflowException: self.handle_workflow_error,
            AuthenticationException: self.handle_authentication_error,
            RateLimitException: self.handle_rate_limit_error,
        }
    
    def handle_validation_error(self, exc: ValidationException) -> JSONResponse:
        """Handle validation errors."""
        error_response = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "field": exc.details.get("field"),
                    "value": exc.details.get("value"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.warning(
            "Validation error",
            extra={
                "error_code": "VALIDATION_ERROR",
                "field": exc.details.get("field"),
                "cause": exc.cause,
                "context": exc.context,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response,
        )
    
    def handle_constraint_error(self, exc: ConstraintException) -> JSONResponse:
        """Handle constraint violation errors."""
        error_response = {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "constraint_type": exc.details.get("constraint_type"),
                    "constraint_details": exc.details.get("constraint_details"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.warning(
            "Constraint violation",
            extra={
                "error_code": "CONSTRAINT_VIOLATION",
                "constraint_type": exc.details.get("constraint_type"),
                "cause": exc.cause,
                "context": exc.context,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response,
        )
    
    def handle_optimization_error(self, exc: OptimizationException) -> JSONResponse:
        """Handle optimization engine errors."""
        error_response = {
            "error": {
                "code": "OPTIMIZATION_ERROR",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "engine": exc.details.get("engine"),
                    "engine_error": exc.details.get("engine_error"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.error(
            "Optimization error",
            extra={
                "error_code": "OPTIMIZATION_ERROR",
                "engine": exc.details.get("engine"),
                "cause": exc.cause,
                "context": exc.context,
            },
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
        )
    
    def handle_database_error(self, exc: DatabaseException) -> JSONResponse:
        """Handle database errors."""
        error_response = {
            "error": {
                "code": "DATABASE_ERROR",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "operation": exc.details.get("operation"),
                    "database_error": exc.details.get("database_error"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.error(
            "Database error",
            extra={
                "error_code": "DATABASE_ERROR",
                "operation": exc.details.get("operation"),
                "cause": exc.cause,
                "context": exc.context,
            },
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
        )
    
    def handle_workflow_error(self, exc: WorkflowException) -> JSONResponse:
        """Handle workflow execution errors."""
        error_response = {
            "error": {
                "code": "WORKFLOW_ERROR",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "stage": exc.details.get("stage"),
                    "workflow_id": exc.details.get("workflow_id"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.error(
            "Workflow error",
            extra={
                "error_code": "WORKFLOW_ERROR",
                "stage": exc.details.get("stage"),
                "cause": exc.cause,
                "context": exc.context,
            },
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
        )
    
    def handle_authentication_error(self, exc: AuthenticationException) -> JSONResponse:
        """Handle authentication errors."""
        error_response = {
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "auth_method": exc.details.get("auth_method"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.warning(
            "Authentication error",
            extra={
                "error_code": "AUTHENTICATION_ERROR",
                "auth_method": exc.details.get("auth_method"),
                "cause": exc.cause,
                "context": exc.context,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response,
        )
    
    def handle_rate_limit_error(self, exc: RateLimitException) -> JSONResponse:
        """Handle rate limit errors."""
        error_response = {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": exc.message,
                "details": {
                    "cause": exc.cause,
                    "context": exc.context,
                    "suggestion": exc.suggestion,
                    "limit": exc.details.get("limit"),
                    "window": exc.details.get("window"),
                    "retry_after": exc.details.get("retry_after"),
                },
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": exc.details.get("request_id"),
        }
        
        self.logger.warning(
            "Rate limit exceeded",
            extra={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "limit": exc.details.get("limit"),
                "window": exc.details.get("window"),
            }
        )
        
        headers = {}
        if exc.details.get("retry_after"):
            headers["Retry-After"] = str(exc.details["retry_after"])
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response,
            headers=headers,
        )
    
    def handle_general_error(self, exc: Exception) -> JSONResponse:
        """Handle general/unexpected errors."""
        error_id = str(exc.__hash__())[:8]
        
        error_response = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "cause": str(exc),
                    "context": "General error handling",
                    "suggestion": "Please try again later or contact support",
                    "error_id": error_id,
                },
            },
            "timestamp": self._get_timestamp(),
        }
        
        self.logger.error(
            "General error",
            extra={
                "error_code": "INTERNAL_ERROR",
                "error_id": error_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            exc_info=True,
        )
        
        # Add stack trace in debug mode
        if settings.DEBUG:
            error_response["error"]["details"]["stack_trace"] = traceback.format_exc()
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
        )
    
    def handle_http_error(self, exc: HTTPException) -> JSONResponse:
        """Handle HTTP errors from FastAPI."""
        error_response = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None,
            },
        }
        
        self.logger.warning(
            "HTTP error",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_error_response(
        self,
        message: str,
        code: str = "CUSTOM_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """
        Create a custom error response.
        
        Args:
            message: Error message
            code: Error code
            status_code: HTTP status code
            details: Additional error details
            
        Returns:
            JSONResponse: Error response
        """
        error_response = {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "timestamp": self._get_timestamp(),
        }
        
        self.logger.error(
            "Custom error response",
            extra={
                "code": code,
                "status_code": status_code,
                "message": message,
            }
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )


class ErrorRecovery:
    """Error recovery and retry mechanisms."""
    
    def __init__(self):
        """Initialize error recovery."""
        self.logger = get_logger(__name__)
    
    async def retry_with_backoff(
        self,
        func,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            max_attempts: Maximum retry attempts
            base_delay: Initial delay
            max_delay: Maximum delay
            exponential_base: Exponential base
            
        Returns:
            Function result
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as exc:
                last_exception = exc
                
                if attempt < max_attempts - 1:
                    # Calculate delay with jitter
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay,
                    )
                    jitter = delay * 0.1  # 10% jitter
                    delay += jitter * (2 * hash(str(exc)) % 2 - 1)
                    
                    self.logger.warning(
                        "Retry attempt failed",
                        extra={
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(exc),
                        }
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        "All retry attempts failed",
                        extra={
                            "max_attempts": max_attempts,
                            "error": str(exc),
                        }
                    )
        
        raise last_exception
    
    def get_recovery_suggestion(self, exc: Exception) -> str:
        """Get recovery suggestion based on exception type."""
        if isinstance(exc, ValidationException):
            return "Check input parameters and try again"
        elif isinstance(exc, ConstraintException):
            return "Adjust constraints or input data"
        elif isinstance(exc, DatabaseException):
            return "Wait and retry, or contact system administrator"
        elif isinstance(exc, OptimizationException):
            return "Try with different parameters or simplify the problem"
        else:
            return "Please try again later or contact support"


# Global error handler instance
error_handler = ErrorHandler()
error_recovery = ErrorRecovery()


# Export key components
__all__ = [
    "ErrorHandler",
    "ErrorRecovery",
    "error_handler",
    "error_recovery",
]