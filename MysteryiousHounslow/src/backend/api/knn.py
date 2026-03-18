from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator, conlist
from typing import List, Optional, Dict, Any
import numpy as np
import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.config import settings
from ..core.db import get_db_connection
from ..core.cache import RedisCache

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer(auto_error=False)

logger = structlog.get_logger(__name__)


# Request/Response Models
class KNNRequest(BaseModel):
    query_vector: conlist(float, min_items=384, max_items=384) = Field(
        ..., description="Query embedding vector (384 dimensions for CLIP)"
    )
    geo_filter: Optional[Dict[str, Any]] = Field(
        None, description="Geographic filter parameters"
    )
    business_rules: Optional[Dict[str, Any]] = Field(
        None, description="Business rule filters"
    )
    max_results: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results (1-100)"
    )
    category_filter: Optional[str] = Field(None, description="Category filter")

    @validator("query_vector")
    def validate_vector_range(cls, v):
        """Validate vector values are in reasonable range."""
        if any(abs(x) > 10 for x in v):  # Basic sanity check
            raise ValueError("Vector values must be between -10 and 10")
        return v


class KNNMatch(BaseModel):
    id: int
    name: str
    category: Optional[str]
    similarity: float
    metadata: Dict[str, Any]


class KNNResponse(BaseModel):
    matches: List[KNNMatch]
    total_matches: int
    execution_time: float
    feature_flag_active: bool


# Feature flag management
FEATURE_HYBRID_KNN = True  # Can be controlled via environment


# Authentication dependency
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Get current user from JWT token."""
    if not credentials:
        # Allow anonymous access for development
        if settings.DEBUG:
            return "anonymous"
        raise HTTPException(status_code=401, detail="Authentication required")

    # In production, validate JWT token here
    # For now, accept any token
    return credentials.credentials


# Rate limiting dependency
async def check_rate_limit(request: Request):
    """Rate limiting check."""
    # Rate limiting is handled by the @limiter.limit decorator
    pass


@router.post("/hybrid_knn", response_model=KNNResponse)
@limiter.limit("100/minute")
async def hybrid_knn_search(
    request: Request,
    data: KNNRequest,
    current_user: Optional[str] = Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """
    Hybrid kNN search combining vector similarity with business rules and geographic filtering.

    Features:
    - Vector similarity search using PostGIS + pgvector
    - Geographic filtering with PostGIS spatial functions
    - Business rule filtering
    - Rate limiting and input validation
    - Feature flag control
    """
    import time

    start_time = time.time()

    logger.info(
        "Hybrid kNN search request",
        user=current_user,
        vector_dim=len(data.query_vector),
        max_results=data.max_results,
        has_geo_filter=bool(data.geo_filter),
        has_business_rules=bool(data.business_rules),
    )

    # Feature flag check
    if not FEATURE_HYBRID_KNN:
        logger.warning("Hybrid kNN feature disabled")
        raise HTTPException(
            status_code=400, detail="Hybrid kNN feature is currently disabled"
        )

    try:
        # Get database connection
        async with get_db_connection() as conn:
            # Convert numpy array to PostgreSQL vector format
            vector_str = f"[{','.join(map(str, data.query_vector))}]"

            # Build query parameters
            params = [
                vector_str,  # query_embedding
                1.0,  # max_distance (cosine distance)
                data.max_results,
                data.category_filter,
            ]

            # Execute kNN search
            rows = await conn.fetch(
                """
                SELECT * FROM find_similar_items($1::vector, $2, $3, $4)
                """,
                *params,
            )

            # Apply additional filters if needed
            matches = []
            for row in rows:
                match = KNNMatch(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    similarity=float(row["similarity"]),
                    metadata=dict(row["metadata"]) if row["metadata"] else {},
                )

                # Apply business rules filtering
                if data.business_rules:
                    if not _apply_business_rules(match, data.business_rules):
                        continue

                # Apply geographic filtering
                if data.geo_filter:
                    if not await _apply_geo_filter(match, data.geo_filter, conn):
                        continue

                matches.append(match)

            execution_time = time.time() - start_time

            # Cache results for performance
            cache = RedisCache()
            cache_key = f"knn:{hash(str(data.dict()))}"
            await cache.set(
                cache_key,
                {
                    "matches": [m.dict() for m in matches],
                    "execution_time": execution_time,
                },
                ttl=300,
            )  # Cache for 5 minutes

            logger.info(
                "Hybrid kNN search completed",
                matches_found=len(matches),
                execution_time=execution_time,
                user=current_user,
            )

            return KNNResponse(
                matches=matches,
                total_matches=len(matches),
                execution_time=execution_time,
                feature_flag_active=FEATURE_HYBRID_KNN,
            )

    except Exception as e:
        logger.error(
            "Hybrid kNN search failed", error=str(e), user=current_user, exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during kNN search"
        )


async def _apply_geo_filter(match: KNNMatch, geo_filter: Dict[str, Any], conn) -> bool:
    """Apply geographic filtering to a match."""
    try:
        # Extract geographic parameters
        lat = geo_filter.get("latitude")
        lng = geo_filter.get("longitude")
        radius = geo_filter.get("radius_km", 10)

        if lat is None or lng is None:
            return True  # No geo filter applied

        # Query item's geographic location
        # This assumes items have geographic data in metadata or separate table
        geo_data = await conn.fetchval(
            """
            SELECT metadata->>'location' FROM items WHERE id = $1
            """,
            match.id,
        )

        if not geo_data:
            return False  # No location data

        # Parse location (assuming JSON format: {"lat": float, "lng": float})
        import json

        location = json.loads(geo_data)

        # Calculate distance using PostGIS (simplified)
        distance_query = """
        SELECT ST_Distance(
            ST_GeomFromText($1, 4326),
            ST_GeomFromText($2, 4326)
        ) / 1000 as distance_km  -- Convert to kilometers
        """

        item_point = f"POINT({location['lng']} {location['lat']})"
        query_point = f"POINT({lng} {lat})"

        distance = await conn.fetchval(distance_query, item_point, query_point)

        return distance <= radius

    except Exception as e:
        logger.warning("Geo filter application failed", match_id=match.id, error=str(e))
        return True  # Allow match if geo filtering fails


def _apply_business_rules(match: KNNMatch, business_rules: Dict[str, Any]) -> bool:
    """Apply business rule filtering to a match."""
    try:
        # Example business rules
        min_similarity = business_rules.get("min_similarity", 0.0)
        if match.similarity < min_similarity:
            return False

        # Category filtering (additional to SQL filter)
        allowed_categories = business_rules.get("allowed_categories")
        if allowed_categories and match.category not in allowed_categories:
            return False

        # Metadata-based rules
        metadata_rules = business_rules.get("metadata_rules", {})
        for key, value in metadata_rules.items():
            if key in match.metadata:
                if isinstance(value, list):
                    if match.metadata[key] not in value:
                        return False
                elif match.metadata[key] != value:
                    return False

        return True

    except Exception as e:
        logger.warning(
            "Business rules application failed", match_id=match.id, error=str(e)
        )
        return True  # Allow match if business rules fail
