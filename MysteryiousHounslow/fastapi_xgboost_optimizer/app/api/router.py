from fastapi import APIRouter

from app.api.endpoints import optimize

api_router = APIRouter()

# Include optimization endpoints
api_router.include_router(optimize.router, prefix="/optimize", tags=["optimization"])
