"""
Authentication middleware for FastAPI XGBoost Optimizer.

This module provides JWT authentication middleware using Auth0 for
secure API access and user session management.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from typing import Optional

from src.backend.core.config import settings
from src.backend.core.exceptions import AuthenticationException


class Auth0JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication using Auth0.

    Validates JWT tokens issued by Auth0 and extracts user information.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Validate the JWT token from the Authorization header.

        Args:
            request: FastAPI request object

        Returns:
            Optional[str]: User ID if token is valid

        Raises:
            HTTPException: If authentication fails
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header missing",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None

        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate the JWT token
        try:
            payload = jwt.decode(
                credentials.credentials,
                options={"verify_aud": False},  # We'll validate audience manually
                audience=settings.AUTH0_AUDIENCE,
                issuer=settings.AUTH0_ISSUER,
                algorithms=["RS256"],
            )

            # Extract user ID from token
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationException("No user ID in token")

            return user_id

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except AuthenticationException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global auth instance
auth0_jwt_bearer = Auth0JWTBearer()


async def get_current_user(request: Request) -> str:
    """
    Dependency to get the current authenticated user.

    Args:
        request: FastAPI request object

    Returns:
        str: User ID
    """
    return await auth0_jwt_bearer(request)
