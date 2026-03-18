"""
API middleware for the FastAPI XGBoost Optimizer.

This module implements custom middleware for logging, rate limiting,
and request/response processing.
"""

import time
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.core.config import settings
from src.backend.core.exceptions import ValidationException
from src.backend.infrastructure.logging_config import get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    def __init__(self, app: ASGIApp):
        """Initialize logging middleware."""
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Log request and response details.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Outgoing response
        """
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        
        # Start timing
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent"),
                "content_length": request.headers.get("content-length"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log successful response
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "content_length": response.headers.get("content-length"),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # Log error
            process_time = time.time() - start_time
            
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "process_time": process_time,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True
            )
            
            # Re-raise exception
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app: ASGIApp):
        """Initialize rate limit middleware."""
        super().__init__(app)
        self.requests = {}
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Apply rate limiting to requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Outgoing response
        """
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            self.logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "method": request.method,
                    "url": str(request.url),
                }
            )
            
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )
        
        # Process request
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get API key first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return f"api_key:{auth_header[7:]}"
        
        # Fall back to IP address
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        import time
        
        current_time = time.time()
        
        # Initialize client data if not exists
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove requests older than 1 minute
        one_minute_ago = current_time - 60
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > one_minute_ago
        ]
        
        # Check if under limit
        rate_limit = settings.RATE_LIMIT_BURST
        if len(self.requests[client_id]) >= rate_limit:
            return False
        
        # Add current request
        self.requests[client_id].append(current_time)
        
        return True


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with additional security headers."""
    
    def __init__(self, app: ASGIApp):
        """Initialize CORS middleware."""
        super().__init__(app)
        self.allowed_origins = set(settings.CORS_ORIGINS)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Apply CORS headers and security policies.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Outgoing response with CORS headers
        """
        # Get origin from request
        origin = request.headers.get("origin")
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.status_code = 200
        
        return response


class GzipMiddleware(BaseHTTPMiddleware):
    """Middleware for Gzip compression."""
    
    def __init__(self, app: ASGIApp, minimum_size: int = 1000):
        """
        Initialize Gzip middleware.
        
        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress
        """
        super().__init__(app)
        self.minimum_size = minimum_size
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Apply Gzip compression to responses.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Possibly compressed response
        """
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_gzip = "gzip" in accept_encoding
        
        # Process request
        response = await call_next(request)
        
        # Apply compression if supported and response is large enough
        if supports_gzip and response.status_code == 200:
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) >= self.minimum_size:
                # Note: In a real implementation, you would compress the response body here
                # This is a simplified version for demonstration
                response.headers["Content-Encoding"] = "gzip"
        
        return response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security enhancements."""
    
    def __init__(self, app: ASGIApp):
        """Initialize security middleware."""
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Apply security policies to requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Outgoing response
        """
        # Validate request content type
        content_type = request.headers.get("content-type", "")
        
        if request.method in ["POST", "PUT"]:
            if content_type and not content_type.startswith("application/json"):
                self.logger.warning(
                    "Invalid content type",
                    extra={
                        "content_type": content_type,
                        "method": request.method,
                        "url": str(request.url),
                    }
                )
                
                return Response(
                    content="Invalid content type",
                    status_code=415,
                    headers={"Content-Type": "text/plain"}
                )
        
        # Check for common attack patterns
        user_agent = request.headers.get("user-agent", "")
        if self._is_suspicious_user_agent(user_agent):
            self.logger.warning(
                "Suspicious user agent",
                extra={
                    "user_agent": user_agent,
                    "client": request.client.host if request.client else "unknown",
                }
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        suspicious_patterns = [
            "sqlmap",
            "nikto",
            "nmap",
            "metasploit",
            "burpsuite",
            "dirbuster",
        ]
        
        return any(pattern in user_agent.lower() for pattern in suspicious_patterns)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""
    
    def __init__(self, app: ASGIApp):
        """Initialize metrics middleware."""
        super().__init__(app)
        self.metrics = {
            "requests_total": 0,
            "requests_by_status": {},
            "requests_by_method": {},
            "response_times": [],
        }
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Collect metrics for requests and responses.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response: Outgoing response
        """
        start_time = time.time()
        
        # Update request counters
        self.metrics["requests_total"] += 1
        self.metrics["requests_by_method"][request.method] = (
            self.metrics["requests_by_method"].get(request.method, 0) + 1
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update metrics
        status_code = str(response.status_code)
        self.metrics["requests_by_status"][status_code] = (
            self.metrics["requests_by_status"].get(status_code, 0) + 1
        )
        
        self.metrics["response_times"].append(response_time)
        
        # Keep only last 1000 response times
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
        
        # Add metrics to response headers
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        response.headers["X-Requests-Total"] = str(self.metrics["requests_total"])
        
        return response
    
    def get_metrics(self) -> dict:
        """Get collected metrics."""
        if not self.metrics["response_times"]:
            avg_response_time = 0
        else:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        
        return {
            "requests_total": self.metrics["requests_total"],
            "requests_by_status": self.metrics["requests_by_status"],
            "requests_by_method": self.metrics["requests_by_method"],
            "average_response_time": avg_response_time,
            "total_response_times": len(self.metrics["response_times"]),
        }