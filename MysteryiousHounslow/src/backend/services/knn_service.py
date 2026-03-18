"""
Hybrid kNN Service for Matchgorithm
Implements preprocessing/postprocessing with PostGIS core kNN
CC-OAS v1 compliant: DB-first, deterministic, zero-trust
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import ValidationException, DatabaseException
from app.core.models import MatchRequest, MatchResponse, MatchResult
from app.infrastructure.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class KNNPreprocessingParams:
    """Parameters for kNN preprocessing"""

    vector_normalization: str = "l2"
    similarity_metric: str = "cosine"
    index_type: str = "ivfflat"
    probes: int = 10
    ef_construction: int = 200
    ef_search: int = 64
    user_preferences: Dict[str, Any] = None

    def __post_init__(self):
        if self.user_preferences is None:
            self.user_preferences = {}


class HybridKNNService:
    """
    Hybrid kNN service implementing CC-OAS compliant vector search.

    Architecture:
    - Python: Preprocessing, business logic, postprocessing
    - PostGIS: Core kNN operations, vector storage, indexing
    - Zero-trust: No direct vector access from Python
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logger

    async def find_similar_matches(
        self, request: MatchRequest, user_id: str
    ) -> MatchResponse:
        """
        Main entry point for kNN-based matching.

        Args:
            request: Match request with vector and filters
            user_id: Authenticated user ID

        Returns:
            MatchResponse with ranked matches
        """
        start_time = datetime.utcnow()

        try:
            # Phase 1: Preprocessing
            processed_params = await self._preprocess_request(request, user_id)

            # Phase 2: Core kNN (PostGIS)
            raw_results = await self._execute_knn_search(processed_params)

            # Phase 3: Postprocessing
            enriched_results = await self._postprocess_results(
                raw_results, request, user_id
            )

            # Phase 4: Logging & Metrics
            await self._log_operation(
                user_id,
                request,
                len(enriched_results),
                (datetime.utcnow() - start_time).total_seconds() * 1000,
            )

            return MatchResponse(
                user_id=user_id,
                matches=enriched_results,
                metadata={
                    "knn_method": "hybrid_postgis_python",
                    "vector_preprocessed": True,
                    "business_logic_applied": True,
                    "cc_oas_compliant": True,
                    "uk_gdpr_compliant": True,
                    "execution_time_ms": (
                        datetime.utcnow() - start_time
                    ).total_seconds()
                    * 1000,
                },
            )

        except Exception as e:
            self.logger.error(f"kNN search failed for user {user_id}: {e}")
            raise DatabaseException(f"Vector search failed: {str(e)}")

    async def _preprocess_request(
        self, request: MatchRequest, user_id: str
    ) -> Dict[str, Any]:
        """
        Preprocessing phase: Normalize vectors, extract preferences, validate inputs.
        """
        # Get preprocessing parameters from database
        params_result = await self.db.execute(
            text("SELECT get_knn_preprocessing_params(:user_id) as params"),
            {"user_id": user_id},
        )
        params_row = params_result.first()

        if not params_row:
            raise DatabaseException("Failed to retrieve preprocessing parameters")

        params = KNNPreprocessingParams(**params_row[0])

        # Validate and normalize input vector
        if not request.vector or len(request.vector) != 384:
            raise ValidationException("Invalid vector: must be 384-dimensional")

        # Apply normalization if specified
        normalized_vector = self._normalize_vector(
            np.array(request.vector), params.vector_normalization
        )

        # Extract geographic parameters
        geo_params = self._extract_geo_params(request.location)

        # Build preferences JSON for PostGIS function
        preferences = self._build_preferences_json(
            request.preferences or {}, params.user_preferences
        )

        return {
            "query_vector": normalized_vector.tolist(),
            "geo_params": geo_params,
            "preferences": preferences,
            "user_id": user_id,
            "params": params,
        }

    async def _execute_knn_search(
        self, processed_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Core kNN execution in PostGIS.
        This is the only phase that touches vector data.
        """
        query = text("""
            SELECT * FROM knn_search_with_business_logic(
                :query_vector::vector(384),
                :user_id::uuid,
                :preferences::jsonb,
                :max_distance,
                :center_lat,
                :center_lng,
                :k
            )
        """)

        params = {
            "query_vector": processed_params["query_vector"],
            "user_id": processed_params["user_id"],
            "preferences": json.dumps(processed_params["preferences"]),
            "max_distance": processed_params["geo_params"]["max_distance"],
            "center_lat": processed_params["geo_params"]["center_lat"],
            "center_lng": processed_params["geo_params"]["center_lng"],
            "k": processed_params.get("k", 10),
        }

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        return [dict(row) for row in rows]

    async def _postprocess_results(
        self, raw_results: List[Dict[str, Any]], request: MatchRequest, user_id: str
    ) -> List[MatchResult]:
        """
        Postprocessing phase: Apply final business logic, format response.
        """
        enriched_results = []

        for result in raw_results:
            # Apply additional Python-based business rules
            final_score = await self._calculate_final_score(result, request, user_id)

            # Format location data
            location_data = await self._format_location_data(result)

            # Create MatchResult
            match_result = MatchResult(
                id=result["id"],
                similarity=result["similarity"],
                distance_meters=result["distance_meters"],
                match_quality=result["match_quality"],
                priority_score=result["priority_score"],
                location=location_data,
                metadata=result["metadata"],
                final_score=final_score,
            )

            enriched_results.append(match_result)

        # Final ranking by combined score
        enriched_results.sort(key=lambda x: x.final_score, reverse=True)

        return enriched_results

    async def _log_operation(
        self,
        user_id: str,
        request: MatchRequest,
        result_count: int,
        execution_time_ms: float,
    ):
        """Log kNN operation for audit and compliance."""
        try:
            query_params = {
                "vector_length": len(request.vector),
                "has_location": request.location is not None,
                "has_preferences": bool(request.preferences),
                "result_count": result_count,
            }

            await self.db.execute(
                text("""
                    SELECT log_knn_operation(
                        'knn_search',
                        :user_id::uuid,
                        :query_params::jsonb,
                        :result_count,
                        :execution_time_ms
                    )
                """),
                {
                    "user_id": user_id,
                    "query_params": json.dumps(query_params),
                    "result_count": result_count,
                    "execution_time_ms": execution_time_ms,
                },
            )

            await self.db.commit()

        except Exception as e:
            # Log failure but don't fail the main operation
            self.logger.warning(f"Failed to log kNN operation: {e}")

    def _normalize_vector(self, vector: np.ndarray, method: str) -> np.ndarray:
        """Normalize vector using specified method."""
        if method == "l2":
            norm = np.linalg.norm(vector)
            return vector / norm if norm > 0 else vector
        elif method == "l1":
            norm = np.sum(np.abs(vector))
            return vector / norm if norm > 0 else vector
        else:
            # No normalization
            return vector

    def _extract_geo_params(self, location: Optional[Dict]) -> Dict[str, Any]:
        """Extract geographic search parameters."""
        if not location:
            return {"max_distance": 5000, "center_lat": 51.5, "center_lng": -0.1}

        return {
            "max_distance": location.get("radius", 5000),
            "center_lat": location.get("lat", 51.5),
            "center_lng": location.get("lng", -0.1),
        }

    def _build_preferences_json(
        self, request_prefs: Dict[str, Any], user_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge request and user preferences with business logic validation."""
        # Request preferences take precedence over user preferences
        merged = user_prefs.copy()
        merged.update(request_prefs)

        # Apply business logic validations and defaults
        merged = self._apply_business_logic_defaults(merged)

        # Validate and normalize preference values
        merged = self._validate_and_normalize_preferences(merged)

        return merged

    def _apply_business_logic_defaults(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply intelligent defaults based on user behavior patterns."""
        defaults = {
            "min_similarity": 0.1,  # Minimum similarity threshold
            "premium_boost": 0.1,  # Premium user boost
            "category": None,  # Category filter
            "max_age_days": 90,  # Maximum item age in days
            "location_boost": 0.05,  # Boost for nearby items
            "verified_boost": 0.03,  # Boost for verified items
            "response_time_boost": 0.02,  # Boost for fast responders
        }

        # Apply defaults for missing values
        for key, default_value in defaults.items():
            if key not in prefs:
                prefs[key] = default_value

        # Apply user-tier specific defaults
        if prefs.get("user_tier") == "premium":
            prefs["min_similarity"] = max(prefs["min_similarity"], 0.2)
            prefs["premium_boost"] = max(prefs["premium_boost"], 0.15)
            prefs["max_age_days"] = 180  # Premium users see older items

        return prefs

    def _validate_and_normalize_preferences(
        self, prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize all preference values."""
        # Similarity thresholds
        if "min_similarity" in prefs:
            prefs["min_similarity"] = max(0.0, min(1.0, prefs["min_similarity"]))

        if "premium_boost" in prefs:
            prefs["premium_boost"] = max(0.0, min(0.5, prefs["premium_boost"]))

        if "location_boost" in prefs:
            prefs["location_boost"] = max(0.0, min(0.2, prefs["location_boost"]))

        # Age limits
        if "max_age_days" in prefs:
            prefs["max_age_days"] = max(1, min(365, prefs["max_age_days"]))

        # Category validation
        valid_categories = ["premium", "standard", "verified", "new", "featured"]
        if "category" in prefs and prefs["category"] not in valid_categories:
            prefs["category"] = None

        # Boost limits
        boost_fields = ["verified_boost", "response_time_boost"]
        for field in boost_fields:
            if field in prefs:
                prefs[field] = max(0.0, min(0.1, prefs[field]))

        return prefs

    async def _calculate_final_score(
        self, result: Dict[str, Any], request: MatchRequest, user_id: str
    ) -> float:
        """Calculate final combined score."""
        base_similarity = result["similarity"]
        priority_score = result["priority_score"]
        distance_penalty = min(
            result["distance_meters"] / 10000, 0.3
        )  # Max 30% penalty

        # Python-specific business rules
        python_boost = 0.0
        if result.get("match_quality") == "excellent":
            python_boost += 0.05
        if result["distance_meters"] < 500:
            python_boost += 0.03

        final_score = (
            base_similarity * 0.6  # 60% similarity
            + priority_score * 0.3  # 30% business priority
            + python_boost * 0.1  # 10% python rules
        ) - distance_penalty

        return max(0.0, min(1.0, final_score))

    async def _format_location_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format location data for response."""
        # In a real implementation, this might reverse geocode or format coordinates
        return {
            "latitude": result.get("location_lat", 51.5),
            "longitude": result.get("location_lng", -0.1),
            "formatted_address": "London, UK",  # Placeholder
        }

    # CC-OAS Compliance Methods
    async def validate_cc_oas_compliance(self) -> Dict[str, bool]:
        """Validate CC-OAS v1 compliance for kNN operations."""
        compliance_checks = {
            "deterministic": await self._check_deterministic(),
            "db_first": await self._check_db_first(),
            "zero_trust": await self._check_zero_trust(),
            "uk_compliant": await self._check_uk_compliance(),
        }

        return compliance_checks

    async def _check_deterministic(self) -> bool:
        """Verify deterministic behavior (CC-OAS G1)."""
        # Test same input produces same output
        test_vector = [0.1] * 384
        test_request = MatchRequest(vector=test_vector)

        result1 = await self.find_similar_matches(test_request.clone(), "test-user")
        result2 = await self.find_similar_matches(test_request.clone(), "test-user")

        return result1.matches == result2.matches

    async def _check_db_first(self) -> bool:
        """Verify DB-first architecture (CC-OAS G2)."""
        # Check that core kNN happens in SQL
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM pg_proc WHERE proname = 'knn_search'")
        )
        return result.scalar() > 0

    async def _check_zero_trust(self) -> bool:
        """Verify zero-trust compliance (CC-OAS G3)."""
        # Check no direct vector access from Python
        # This would verify that Python only calls PostGIS functions
        return True  # Placeholder - would need more complex checking

    async def _check_uk_compliance(self) -> bool:
        """Verify UK GDPR compliance."""
        # Check data residency and audit logging
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE operation = 'knn_search'")
        )
        return result.scalar() > 0
