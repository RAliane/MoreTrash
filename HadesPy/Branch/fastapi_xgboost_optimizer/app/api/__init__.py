"""
API layer for the FastAPI XGBoost Optimizer.

This package handles HTTP endpoints, request/response validation,
and API-specific middleware.
"""

from fastapi import APIRouter

# Create the main API router
router = APIRouter()

__all__ = ["router"]