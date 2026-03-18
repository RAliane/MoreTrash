"""
Structured logging configuration for the FastAPI XGBoost Optimizer.

This module provides comprehensive logging setup with JSON formatting,
context tracking, and multiple log levels for production monitoring.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pythonjsonlogger import jsonlogger

from src.backend.core.config import settings


# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
microtask_id_var: ContextVar[Optional[str]] = ContextVar("microtask_id", default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record["timestamp"] = time.time()
        
        # Add log level
        log_record["level"] = record.levelname
        
        # Add logger name
        log_record["logger"] = record.name
        
        # Add request context
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id
        
        microtask_id = microtask_id_var.get()
        if microtask_id:
            log_record["microtask_id"] = microtask_id
        
        # Add application info
        log_record["app"] = settings.APP_NAME
        log_record["version"] = settings.APP_VERSION
        log_record["environment"] = settings.ENVIRONMENT
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }


def setup_logging() -> None:
    """
    Set up structured logging for the application.
    
    Configures both standard library logging and structlog for
    comprehensive logging with JSON formatting and context tracking.
    """
    
    # Configure standard library logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Set formatter based on configuration
    if settings.LOG_FORMAT == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if configured
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if settings.LOG_FORMAT == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


class LoggingContext:
    """Context manager for temporary logging context."""
    
    def __init__(self, **kwargs):
        """
        Initialize logging context.
        
        Args:
            **kwargs: Context variables to set
        """
        self.context_vars = kwargs
        self.tokens = {}
    
    def __enter__(self):
        """Enter logging context."""
        for key, value in self.context_vars.items():
            if key == "request_id":
                self.tokens[key] = request_id_var.set(value)
            elif key == "microtask_id":
                self.tokens[key] = microtask_id_var.set(value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context."""
        for key, token in self.tokens.items():
            if key == "request_id":
                request_id_var.reset(token)
            elif key == "microtask_id":
                microtask_id_var.reset(token)


class RequestLoggingMiddleware:
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        """Initialize middleware."""
        self.app = app
        self.logger = get_logger(__name__)
    
    async def __call__(self, scope, receive, send):
        """Process request/response."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate request ID if not present
        request_id = None
        headers = dict(scope.get("headers", []))
        
        if b"x-request-id" in headers:
            request_id = headers[b"x-request-id"].decode()
        else:
            request_id = str(uuid4())
        
        # Set request context
        with LoggingContext(request_id=request_id):
            # Log request start
            self.logger.info(
                "Request started",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "query_string": scope.get("query_string", b"").decode(),
                    "client": scope.get("client"),
                    "request_id": request_id,
                }
            )
            
            start_time = time.time()
            
            # Process request
            try:
                await self.app(scope, receive, send)
                
                # Log successful completion
                duration = time.time() - start_time
                self.logger.info(
                    "Request completed",
                    extra={
                        "duration": duration,
                        "request_id": request_id,
                    }
                )
                
            except Exception as exc:
                # Log error
                duration = time.time() - start_time
                self.logger.error(
                    "Request failed",
                    extra={
                        "duration": duration,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "request_id": request_id,
                    },
                    exc_info=True,
                )
                raise


class PerformanceLogging:
    """Decorator for performance logging."""
    
    def __init__(self, operation: str = None):
        """
        Initialize performance logger.
        
        Args:
            operation: Operation name for logging
        """
        self.operation = operation
    
    def __call__(self, func):
        """Decorate function with performance logging."""
        logger = get_logger(func.__module__)
        operation = self.operation or func.__name__
        
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            logger.info(
                f"{operation} started",
                extra={"operation": operation},
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"{operation} completed",
                    extra={
                        "operation": operation,
                        "duration": duration,
                    },
                )
                
                return result
                
            except Exception as exc:
                duration = time.time() - start_time
                
                logger.error(
                    f"{operation} failed",
                    extra={
                        "operation": operation,
                        "duration": duration,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                    exc_info=True,
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            logger.info(
                f"{operation} started",
                extra={"operation": operation},
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"{operation} completed",
                    extra={
                        "operation": operation,
                        "duration": duration,
                    },
                )
                
                return result
                
            except Exception as exc:
                duration = time.time() - start_time
                
                logger.error(
                    f"{operation} failed",
                    extra={
                        "operation": operation,
                        "duration": duration,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                    exc_info=True,
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class MetricsCollector:
    """Collect and aggregate performance metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            "requests_total": 0,
            "requests_by_status": {},
            "requests_by_method": {},
            "response_times": [],
            "errors_total": 0,
            "errors_by_type": {},
            "start_time": time.time(),
        }
        self.logger = get_logger(__name__)
    
    def record_request_start(self, request_id: str, method: str) -> None:
        """Record request start."""
        self.metrics["requests_total"] += 1
        self.metrics["requests_by_method"][method] = (
            self.metrics["requests_by_method"].get(method, 0) + 1
        )
        
        self.logger.debug(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "requests_total": self.metrics["requests_total"],
            },
        )
    
    def record_request_complete(
        self, request_id: str, status: int, duration: float
    ) -> None:
        """Record request completion."""
        # Update status counts
        status_str = str(status)
        self.metrics["requests_by_status"][status_str] = (
            self.metrics["requests_by_status"].get(status_str, 0) + 1
        )
        
        # Record response time
        self.metrics["response_times"].append(duration)
        
        # Keep only last 1000 response times
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
        
        self.logger.debug(
            "Request completed",
            extra={
                "request_id": request_id,
                "status": status,
                "duration": duration,
            },
        )
    
    def record_request_error(self, request_id: str, error: str) -> None:
        """Record request error."""
        self.metrics["errors_total"] += 1
        self.metrics["errors_by_type"][error] = (
            self.metrics["errors_by_type"].get(error, 0) + 1
        )
        
        self.logger.error(
            "Request error",
            extra={
                "request_id": request_id,
                "error": error,
            },
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if not self.metrics["response_times"]:
            avg_response_time = 0
            p95_response_time = 0
        else:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            p95_response_time = sorted(self.metrics["response_times"])[
                int(len(self.metrics["response_times"]) * 0.95)
            ]
        
        return {
            "uptime": time.time() - self.metrics["start_time"],
            "requests_total": self.metrics["requests_total"],
            "requests_per_minute": self.metrics["requests_total"] / max(1, (time.time() - self.metrics["start_time"]) / 60),
            "average_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "error_rate": self.metrics["errors_total"] / max(1, self.metrics["requests_total"]),
            "requests_by_status": self.metrics["requests_by_status"].copy(),
            "requests_by_method": self.metrics["requests_by_method"].copy(),
            "errors_by_type": self.metrics["errors_by_type"].copy(),
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


def log_execution_time(logger: structlog.BoundLogger, operation: str):
    """Context manager for logging execution time."""
    class ExecutionTimer:
        def __enter__(self):
            self.start_time = time.time()
            logger.info(f"{operation} started")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            if exc_type is None:
                logger.info(f"{operation} completed", extra={"duration": duration})
            else:
                logger.error(
                    f"{operation} failed",
                    extra={
                        "duration": duration,
                        "error": str(exc_val),
                        "error_type": exc_type.__name__,
                    },
                )
    
    return ExecutionTimer()


# Export key components
__all__ = [
    "setup_logging",
    "get_logger",
    "LoggingContext",
    "RequestLoggingMiddleware",
    "PerformanceLogging",
    "MetricsCollector",
    "metrics_collector",
    "log_execution_time",
]