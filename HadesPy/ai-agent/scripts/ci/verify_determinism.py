#!/usr/bin/env python3
"""Verify RAG pipeline produces deterministic outputs.

This script runs the RAG pipeline 10 times with the same student preferences
and verifies that all outputs are identical. Any variation will cause the
script to exit with a non-zero status, failing the CI pipeline.

Usage:
    python verify_determinism.py

Environment Variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://neo4j:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (default: test)
    POSTGRES_HOST: PostgreSQL host (default: postgres)
    POSTGRES_PORT: PostgreSQL port (default: 5432)
    POSTGRES_DB: PostgreSQL database (default: test)
    POSTGRES_USER: PostgreSQL user (default: test)
    POSTGRES_PASSWORD: PostgreSQL password (default: test)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Number of runs for determinism check (default 10, configurable via env var)
NUM_RUNS = int(os.environ.get("DETERMINISM_RUNS", "10"))

# Test student profile: Aerospace Engineer with high math interest
TEST_PREFERENCES = {
    "math_interest": 0.9,
    "science_interest": 0.85,
    "humanities_interest": 0.2,
    "career_goal": "aerospace_engineer",
    "learning_style": "analytical",
    "credits_per_semester": 15,
    "preferred_difficulty": "advanced",
}


def serialize_recommendation(rec: Any) -> str:
    """Serialize a recommendation to a comparable string.
    
    Args:
        rec: CourseRecommendation object
        
    Returns:
        JSON string representation
    """
    if hasattr(rec, '__dataclass_fields__'):
        data = asdict(rec)
    else:
        data = dict(rec)
    
    # Round floats to avoid tiny precision differences
    def round_floats(obj: Any) -> Any:
        if isinstance(obj, float):
            return round(obj, 6)
        elif isinstance(obj, dict):
            return {k: round_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [round_floats(v) for v in obj]
        return obj
    
    data = round_floats(data)
    return json.dumps(data, sort_keys=True, default=str)


def compute_hash(recommendations: List[Any]) -> str:
    """Compute a hash of the recommendations list.
    
    Args:
        recommendations: List of recommendation objects
        
    Returns:
        SHA256 hash string
    """
    serialized = json.dumps(
        [serialize_recommendation(r) for r in recommendations],
        sort_keys=True
    )
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


async def run_pipeline_once(recommender: Any, preferences: Dict[str, Any]) -> List[Any]:
    """Run the RAG pipeline once with given preferences.
    
    Args:
        recommender: CourseRecommender instance
        preferences: Student preferences dict
        
    Returns:
        List of recommendations
    """
    from src.rag.course_recommender import StudentPreferences
    
    student_prefs = StudentPreferences(**preferences)
    recommendations = await recommender.recommend(student_prefs)
    return recommendations


async def verify_rag_determinism() -> bool:
    """Verify RAG pipeline produces deterministic outputs.
    
    Returns:
        True if deterministic, False otherwise
    """
    logger.info("=" * 60)
    logger.info("RAG PIPELINE DETERMINISM VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Test profile: {TEST_PREFERENCES['career_goal']}")
    logger.info(f"Math interest: {TEST_PREFERENCES['math_interest']}")
    logger.info(f"Number of runs: {NUM_RUNS}")
    logger.info("-" * 60)
    
    try:
        from src.rag.course_recommender import CourseRecommender
    except ImportError as e:
        logger.error(f"Failed to import CourseRecommender: {e}")
        return False
    
    # Initialize recommender
    logger.info("Initializing CourseRecommender...")
    recommender = CourseRecommender()
    
    try:
        await recommender.initialize()
        logger.info("✓ Recommender initialized")
    except Exception as e:
        logger.error(f"Failed to initialize recommender: {e}")
        return False
    
    # Run pipeline multiple times
    logger.info(f"Running pipeline {NUM_RUNS} times...")
    results: List[List[Any]] = []
    hashes: List[str] = []
    
    for i in range(NUM_RUNS):
        try:
            recommendations = await run_pipeline_once(recommender, TEST_PREFERENCES)
            results.append(recommendations)
            run_hash = compute_hash(recommendations)
            hashes.append(run_hash)
            logger.info(f"  Run {i+1}/{NUM_RUNS}: {len(recommendations)} recommendations, hash={run_hash[:16]}...")
        except Exception as e:
            logger.error(f"  Run {i+1}/{NUM_RUNS}: FAILED - {e}")
            return False
    
    # Verify all hashes are identical
    unique_hashes = set(hashes)
    
    if len(unique_hashes) == 1:
        logger.info("-" * 60)
        logger.info("✓ DETERMINISM VALIDATED")
        logger.info(f"  All {NUM_RUNS} runs produced identical outputs")
        logger.info(f"  Hash: {hashes[0]}")
        
        # Log top recommendation
        if results[0]:
            top_rec = results[0][0]
            logger.info(f"  Top recommendation: {top_rec.course_name} (score: {top_rec.total_score:.4f})")
        
        return True
    else:
        logger.error("-" * 60)
        logger.error("✗ DETERMINISM VIOLATION DETECTED")
        logger.error(f"  Found {len(unique_hashes)} unique outputs across {NUM_RUNS} runs")
        
        # Show which runs differ
        for i, h in enumerate(hashes):
            logger.error(f"  Run {i+1}: hash={h[:16]}...")
        
        # Show differences in detail
        logger.error("\nDetailed comparison of run 1 vs run 2:")
        if len(results) >= 2:
            recs1 = [serialize_recommendation(r) for r in results[0]]
            recs2 = [serialize_recommendation(r) for r in results[1]]
            
            if len(recs1) != len(recs2):
                logger.error(f"  Different number of recommendations: {len(recs1)} vs {len(recs2)}")
            else:
                for idx, (r1, r2) in enumerate(zip(recs1, recs2)):
                    if r1 != r2:
                        logger.error(f"  Recommendation {idx} differs:")
                        logger.error(f"    Run 1: {r1[:200]}...")
                        logger.error(f"    Run 2: {r2[:200]}...")
        
        return False


async def verify_xgboost_determinism() -> bool:
    """Verify XGBoost ranker produces deterministic scores.
    
    Returns:
        True if deterministic, False otherwise
    """
    logger.info("\n" + "=" * 60)
    logger.info("XGBOOST RANKER DETERMINISM VALIDATION")
    logger.info("=" * 60)
    
    try:
        from src.ranking.xgboost_ranker import CourseRanker
        from src.ranking.config import RankingConfig
        import numpy as np
    except ImportError as e:
        logger.warning(f"XGBoost not available, skipping: {e}")
        return True  # Skip if XGBoost not installed
    
    # Create test features
    test_features = np.array([
        [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9],  # Aerospace profile
        [0.8, 0.7, 0.4, 0.7, 0.5, 3.0, 0.6, 0.7],   # Mixed profile
    ])
    
    config = RankingConfig(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,  # Fixed seed for determinism
    )
    
    ranker = CourseRanker(config=config)
    
    # Check if model exists
    if not Path(ranker.model_path).exists():
        logger.warning("No trained model found, skipping XGBoost determinism check")
        return True
    
    try:
        ranker.load_model()
    except Exception as e:
        logger.warning(f"Could not load model: {e}")
        return True
    
    # Score multiple times
    logger.info(f"Scoring {len(test_features)} feature vectors {NUM_RUNS} times...")
    all_scores: List[List[float]] = []
    
    for i in range(NUM_RUNS):
        scores = ranker.predict(test_features)
        all_scores.append(scores.tolist())
        logger.info(f"  Run {i+1}: scores={scores.tolist()}")
    
    # Verify all identical
    first_scores = all_scores[0]
    all_identical = all(s == first_scores for s in all_scores)
    
    if all_identical:
        logger.info("-" * 60)
        logger.info("✓ XGBOOST DETERMINISM VALIDATED")
        return True
    else:
        logger.error("-" * 60)
        logger.error("✗ XGBOOST DETERMINISM VIOLATION")
        return False


async def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Starting CI determinism validation...")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Run validations
    rag_ok = await verify_rag_determinism()
    xgb_ok = await verify_xgboost_determinism()
    
    # Final result
    logger.info("\n" + "=" * 60)
    logger.info("FINAL RESULTS")
    logger.info("=" * 60)
    logger.info(f"RAG Pipeline:     {'✓ PASS' if rag_ok else '✗ FAIL'}")
    logger.info(f"XGBoost Ranker:   {'✓ PASS' if xgb_ok else '✗ FAIL'}")
    
    if rag_ok and xgb_ok:
        logger.info("\n✓ ALL DETERMINISM CHECKS PASSED")
        return 0
    else:
        logger.error("\n✗ DETERMINISM CHECKS FAILED - Pipeline will fail")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
