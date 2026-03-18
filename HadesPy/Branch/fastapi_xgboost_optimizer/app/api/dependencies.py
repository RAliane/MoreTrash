"""
API dependencies for the FastAPI XGBoost Optimizer.

This module defines reusable dependencies for authentication, rate limiting,
database sessions, and other cross-cutting concerns.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationException, RateLimitException
from app.database.postgis_client import PostGISClient

# Security scheme
security = HTTPBearer(auto_error=False)


async def authenticate_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
) -> str:
    """
    Authenticate requests using API key.
    
    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request object
        
    Returns:
        str: Authenticated API key
        
    Raises:
        HTTPException: If authentication fails
    """
    # Check for API key in header
    if credentials:
        api_key = credentials.credentials
    else:
        # Check for API key in custom header
        api_key = request.headers.get(settings.API_KEY_HEADER)
    
    # If no API key provided, check if authentication is required
    if not api_key:
        if not settings.ALLOWED_API_KEYS:
            # No authentication required
            return "anonymous"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Validate API key
    if settings.ALLOWED_API_KEYS and api_key not in settings.ALLOWED_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key


async def get_request_id(request: Request) -> str:
    """
    Get or generate request ID for tracking.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Request ID
    """
    # Check if request ID is provided in headers
    request_id = request.headers.get("X-Request-ID")
    
    if not request_id:
        # Generate new request ID
        request_id = str(uuid.uuid4())
    
    return request_id


class RateLimiterDependency:
    """Rate limiter dependency for API endpoints."""
    
    def __init__(self):
        self.requests = {}
        self.cleanup_task = None
    
    async def __call__(
        self,
        request: Request,
        api_key: str = Depends(authenticate_api_key),
    ) -> None:
        """
        Check rate limit for the request.
        
        Args:
            request: FastAPI request object
            api_key: Authenticated API key
            
        Raises:
            RateLimitException: If rate limit is exceeded
        """
        # Simple in-memory rate limiting (could be replaced with Redis)
        import time
        
        current_time = time.time()
        client_id = api_key if api_key != "anonymous" else request.client.host
        
        # Clean up old entries
        await self._cleanup_old_entries(current_time)
        
        # Check current request count
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove requests older than 1 minute
        one_minute_ago = current_time - 60
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > one_minute_ago
        ]
        
        # Check rate limit
        rate_limit = 100  # requests per minute
        if len(self.requests[client_id]) >= rate_limit:
            raise RateLimitException(
                message="Rate limit exceeded",
                limit=rate_limit,
                window="1 minute",
                retry_after=60
            )
        
        # Add current request
        self.requests[client_id].append(current_time)
    
    async def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old request entries."""
        if self.cleanup_task and not self.cleanup_task.done():
            return
        
        # Run cleanup every 5 minutes
        if current_time % 300 < 1:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_entries())
    
    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired request entries."""
        import time
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > one_hour_ago
            ]
            
            if not self.requests[client_id]:
                del self.requests[client_id]


# Global rate limiter instance
rate_limiter = RateLimiterDependency()


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    Yields:
        AsyncSession: Database session
    """
    from app.database.postgis_client import PostGISClient
    
    client = PostGISClient()
    session = await client.get_session()
    
    try:
        yield session
    finally:
        await session.close()


class PaginationParams:
    """Pagination parameters dependency."""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ):
        """
        Initialize pagination parameters.
        
        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
        """
        self.skip = max(0, skip)
        self.limit = min(1000, max(1, limit))  # Limit between 1 and 1000
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else "asc"
        
        if self.sort_order not in ["asc", "desc"]:
            self.sort_order = "asc"


async def get_pagination_params(
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
) -> PaginationParams:
    """
    Get pagination parameters.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        PaginationParams: Pagination parameters
    """
    return PaginationParams(skip, limit, sort_by, sort_order)


class CacheDependency:
    """Simple in-memory cache dependency."""
    
    def __init__(self):
        self.cache = {}
        self.ttl = 300  # 5 minutes TTL
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        import time
        
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        import time
        self.cache[key] = (value, time.time())
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()


# Global cache instance
cache = CacheDependency()


async def get_cache() -> CacheDependency:
    """Get cache dependency."""
    return cache


class ValidationDependency:
    """Request validation dependency."""
    
    async def __call__(self, request: Request) -> None:
        """
        Validate incoming request.
        
        Args:
            request: FastAPI request object
            
        Raises:
            ValidationException: If request is invalid
        """
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 10:  # 10MB limit
                    raise ValidationException(
                        message="Request too large",
                        details={"max_size_mb": 10, "actual_size_mb": size_mb}
                    )
            except ValueError:
                pass  # Invalid content-length header
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT"]:
            content_type = request.headers.get("content-type")
            if content_type and not content_type.startswith("application/json"):
                raise ValidationException(
                    message="Invalid content type",
                    details={"expected": "application/json", "actual": content_type}
                )


# Global validation instance
validation = ValidationDependency()


async def get_validation() -> ValidationDependency:
    """Get validation dependency."""
    return validation