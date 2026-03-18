from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Matchgorithm ML Pipeline",
    description="AI-powered matching pipeline with constraint optimization",
    version="1.0.0",
)


# Configuration
class Config:
    HASURA_URL = os.getenv("HASURA_URL", "http://localhost:8080/v1/graphql")
    HASURA_ADMIN_SECRET = os.getenv("HASURA_ADMIN_SECRET", "")
    DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://localhost:8055")
    DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")


# Pydantic models
class Location(BaseModel):
    lat: float
    lng: float


class FetchCandidatesRequest(BaseModel):
    location: Location
    radius: int = 5000
    filters: Optional[Dict[str, Any]] = None


class Candidate(BaseModel):
    id: str
    embedding: List[float]
    metadata: Dict[str, Any]
    constraints: Dict[str, Any]
    score: Optional[float] = None


class MatchRequest(BaseModel):
    user_id: str
    candidates: List[Candidate]
    constraints: Dict[str, Any]


class MatchResult(BaseModel):
    user_id: str
    matches: List[Dict[str, Any]]
    optimization_score: float


# Import pipeline stages
from .pipeline import MatchingPipeline

pipeline = MatchingPipeline()


@app.post("/api/pipeline/fetch-candidates", response_model=List[Candidate])
async def fetch_candidates(request: FetchCandidatesRequest):
    """Fetch pre-filtered candidates from Hasura"""
    try:
        candidates = await pipeline.fetch_candidates(
            request.location.lat, request.location.lng, request.radius, request.filters
        )
        return candidates
    except Exception as e:
        logger.error(f"Error fetching candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/match", response_model=MatchResult)
async def run_matching_pipeline(request: MatchRequest):
    """Run the complete matching pipeline"""
    try:
        result = await pipeline.run_pipeline(
            request.user_id, request.candidates, request.constraints
        )
        return result
    except Exception as e:
        logger.error(f"Error running matching pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ml-pipeline"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
