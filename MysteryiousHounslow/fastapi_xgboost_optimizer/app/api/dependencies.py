from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

from app.infrastructure.config import settings

security = HTTPBearer(auto_error=False)


async def validate_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Validate API key from Authorization header.

    In production, this should validate against a database or external service.
    For development, we accept any non-empty API key.
    """
    if not settings.REQUIRE_API_KEY:
        return "development-key"

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials

    # In production, validate against stored API keys
    # For now, accept any non-empty key in development
    if not api_key or len(api_key.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key


async def get_current_user(api_key: str = Depends(validate_api_key)) -> Optional[dict]:
    """
    Get current user information from API key.

    In production, this would decode a JWT or look up user info.
    For development, return mock user data.
    """
    # Mock user data - in production, decode JWT or query database
    return {
        "user_id": "user-123",
        "api_key": api_key,
        "permissions": ["optimize:read", "optimize:write"],
    }
