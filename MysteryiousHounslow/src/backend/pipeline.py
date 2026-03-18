"""
Matching Pipeline - Orchestrates XGBoost, OR-Tools, and PyGAD

This module implements the core matching algorithm pipeline:
1. Fetch pre-filtered candidates from Hasura
2. Rank with XGBoost
3. Apply hard constraints with OR-Tools
4. Optimize soft constraints with PyGAD
5. Return optimized matches
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from src.backend.optimization.xgboost_engine import XGBoostEngine
from src.backend.optimization.constraint_solver import ConstraintSolver
from src.backend.optimization.genetic_optimizer import GeneticOptimizer
from src.backend.database.hasura_client import HasuraClient

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    id: str
    embedding: List[float]
    metadata: Dict[str, Any]
    constraints: Dict[str, Any]
    score: Optional[float] = None


@dataclass
class MatchResult:
    user_id: str
    matches: List[Dict[str, Any]]
    optimization_score: float


class MatchingPipeline:
    """Orchestrates the complete matching pipeline"""

    def __init__(self):
        self.hasura_client = HasuraClient()
        self.xgboost_engine = XGBoostEngine()
        self.constraint_solver = ConstraintSolver()
        self.genetic_optimizer = GeneticOptimizer()

    async def initialize(self):
        """Initialize all pipeline components"""
        await self.hasura_client.initialize()
        await self.xgboost_engine.load_models()
        logger.info("Matching pipeline initialized")

    async def fetch_candidates(
        self,
        lat: float,
        lng: float,
        radius: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Candidate]:
        """Fetch pre-filtered candidates from Hasura"""
        query = """
        query FetchCandidates($lat: float8!, $lng: float8!, $radius: Int!, $filters: jsonb) {
          candidates(
            where: {
              location: { _st_d_within: { point: { lat: $lat, lng: $lng }, distance: $radius } }
              status: { _eq: "active" }
              _and: $filters
            }
            limit: 1000
          ) {
            id
            embedding
            metadata
            constraints
          }
        }
        """

        variables = {"lat": lat, "lng": lng, "radius": radius, "filters": filters or {}}

        result = await self.hasura_client.query(query, variables)

        candidates = []
        for item in result["data"]["candidates"]:
            candidates.append(
                Candidate(
                    id=item["id"],
                    embedding=item["embedding"],
                    metadata=item["metadata"],
                    constraints=item["constraints"],
                )
            )

        logger.info(f"Fetched {len(candidates)} candidates")
        return candidates

    async def run_pipeline(
        self, user_id: str, candidates: List[Candidate], constraints: Dict[str, Any]
    ) -> MatchResult:
        """Run the complete matching pipeline"""

        # Stage 1: XGBoost ranking
        logger.info("Stage 1: XGBoost ranking")
        ranked_candidates = await self.xgboost_engine.rank_candidates(candidates)

        # Stage 2: Constraint solving with OR-Tools
        logger.info("Stage 2: Constraint solving")
        feasible_matches = await self.constraint_solver.solve_constraints(
            ranked_candidates, constraints
        )

        # Stage 3: Genetic optimization with PyGAD
        logger.info("Stage 3: Genetic optimization")
        optimized_matches, score = await self.genetic_optimizer.optimize(
            feasible_matches, constraints
        )

        # Convert to MatchResult format
        matches = []
        for match_data in optimized_matches:
            matches.append(
                {
                    "candidate_id": match_data["id"],
                    "score": match_data["score"],
                    "rank": match_data["rank"],
                    "constraints_satisfied": match_data["constraints_satisfied"],
                }
            )

        # Stage 4: Write results back to Hasura
        logger.info("Stage 4: Writing results to Hasura")
        affected_rows = await self.hasura_client.update_match_results(user_id, matches)

        result = MatchResult(user_id=user_id, matches=matches, optimization_score=score)

        logger.info(
            f"Pipeline completed for user {user_id}: {len(matches)} matches, score {score}, updated {affected_rows} rows"
        )
        return result

    async def cleanup(self):
        """Cleanup pipeline resources"""
        await self.hasura_client.close()
        await self.xgboost_engine.cleanup()
        logger.info("Matching pipeline cleaned up")
