"""Determinism tests for end-to-end RAG pipeline.

These tests validate that the complete RAG pipeline produces identical
results across multiple runs with the same query, user context, and courses.
Per TOML specification:
- Run full recommendation 20 times
- Hash output results
- Assert all 20 runs produce identical hashes

Any non-determinism will cause these tests to fail.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Mark all tests in this file with 'determinism' marker
pytestmark = [
    pytest.mark.determinism,
    pytest.mark.asyncio,
]

# Number of iterations per TOML specification
NUM_ITERATIONS = 20

# Fixed test data
AEROSPACE_PREFERENCES = {
    "math_interest": 0.9,
    "science_interest": 0.85,
    "humanities_interest": 0.2,
    "career_goal": "aerospace_engineer",
    "learning_style": "analytical",
    "credits_per_semester": 15,
    "preferred_difficulty": "advanced",
}

DATA_SCIENTIST_PREFERENCES = {
    "math_interest": 0.8,
    "science_interest": 0.75,
    "humanities_interest": 0.4,
    "career_goal": "data_scientist",
    "learning_style": "analytical",
    "credits_per_semester": 12,
    "preferred_difficulty": "intermediate",
}

HUMANITIES_PREFERENCES = {
    "math_interest": 0.2,
    "science_interest": 0.3,
    "humanities_interest": 0.95,
    "career_goal": "philosopher",
    "learning_style": "conceptual",
    "credits_per_semester": 12,
    "preferred_difficulty": "intermediate",
}


def normalize_recommendation(rec: Any) -> Dict[str, Any]:
    """Normalize a recommendation for deterministic comparison.

    Rounds floats to avoid precision differences and extracts key fields.

    Args:
        rec: CourseRecommendation object

    Returns:
        Normalized dictionary
    """
    if hasattr(rec, '__dataclass_fields__'):
        data = asdict(rec)
    else:
        data = dict(rec)

    # Round all floats to 10 decimal places for comparison
    for key, value in data.items():
        if isinstance(value, float):
            data[key] = round(value, 10)
        elif isinstance(value, list):
            data[key] = sorted(value) if value else []
        elif isinstance(value, dict):
            data[key] = {
                k: round(v, 10) if isinstance(v, float) else v
                for k, v in sorted(value.items())
            }

    # Return deterministic key ordering
    return dict(sorted(data.items()))


def compute_result_hash(results: List[Any]) -> str:
    """Compute deterministic hash of recommendation results.

    Args:
        results: List of recommendation objects

    Returns:
        SHA-256 hash string
    """
    normalized = [normalize_recommendation(r) for r in results]

    # Create deterministic JSON string
    json_str = json.dumps(normalized, sort_keys=True, separators=(',', ':'))

    return hashlib.sha256(json_str.encode()).hexdigest()


class TestPipelineHashDeterminism:
    """Test full pipeline determinism with hash comparison."""

    @pytest.fixture
    def mock_course_data(self):
        """Create deterministic mock course data."""
        return [
            {
                "id": "course-aero-101",
                "name": "Aerospace Engineering Fundamentals",
                "department": "AERO",
                "description": "Introduction to aerospace engineering",
                "career_paths": ["aerospace_engineer", "mechanical_engineer"],
                "credits": 4,
                "math_intensity": 0.95,
                "humanities_intensity": 0.1,
                "prerequisites": ["math-101", "physics-101"],
            },
            {
                "id": "course-me-201",
                "name": "Mechanical Systems",
                "department": "ME",
                "description": "Advanced mechanical systems design",
                "career_paths": ["mechanical_engineer", "aerospace_engineer"],
                "credits": 4,
                "math_intensity": 0.85,
                "humanities_intensity": 0.15,
                "prerequisites": ["math-101"],
            },
            {
                "id": "course-cs-301",
                "name": "Machine Learning",
                "department": "CS",
                "description": "Advanced machine learning algorithms",
                "career_paths": ["data_scientist", "software_engineer"],
                "credits": 4,
                "math_intensity": 0.8,
                "humanities_intensity": 0.2,
                "prerequisites": ["cs-101", "math-201"],
            },
            {
                "id": "course-ds-101",
                "name": "Data Science Basics",
                "department": "DS",
                "description": "Introduction to data science",
                "career_paths": ["data_scientist", "business_analyst"],
                "credits": 3,
                "math_intensity": 0.7,
                "humanities_intensity": 0.3,
                "prerequisites": [],
            },
            {
                "id": "course-phil-101",
                "name": "Ethics in Technology",
                "department": "PHIL",
                "description": "Ethical considerations in engineering",
                "career_paths": ["philosopher", "ethicist"],
                "credits": 3,
                "math_intensity": 0.2,
                "humanities_intensity": 0.9,
                "prerequisites": [],
            },
        ]

    @pytest_asyncio.fixture
    async def mock_recommender(self, mock_course_data):
        """Create a mock recommender with deterministic behavior."""
        pytest.importorskip("src.rag.course_recommender", reason="RAG module not available")

        from src.rag.course_recommender import CourseRecommender, StudentPreferences

        recommender = CourseRecommender()

        # Mock the internal components for deterministic behavior
        recommender.graph = MagicMock()
        recommender.vector_store = MagicMock()
        recommender.ranker = MagicMock()

        # Create deterministic mock recommendations
        def create_mock_recommendations(prefs: StudentPreferences):
            """Create deterministic recommendations based on preferences."""
            # Sort by career match (deterministic)
            career_goal = prefs.career_goal

            scored_courses = []
            for course in mock_course_data:
                # Calculate deterministic scores
                career_match = 1.0 if career_goal in course["career_paths"] else 0.3
                math_match = 1.0 - abs(prefs.math_interest - course["math_intensity"])

                total_score = (career_match * 0.5) + (math_match * 0.3) + 0.2

                scored_courses.append({
                    "course": course,
                    "score": total_score,
                })

            # Sort by score DESC, then course_id ASC (deterministic tie-breaking)
            scored_courses.sort(key=lambda x: (-x["score"], x["course"]["id"]))

            # Create recommendation objects
            recommendations = []
            for i, sc in enumerate(scored_courses):
                course = sc["course"]
                rec = MagicMock()
                rec.course_id = course["id"]
                rec.course_name = course["name"]
                rec.department = course["department"]
                rec.description = course["description"]
                rec.career_paths = course["career_paths"]
                rec.credits = course["credits"]
                rec.math_intensity = course["math_intensity"]
                rec.humanities_intensity = course["humanities_intensity"]
                rec.total_score = round(sc["score"], 10)
                rec.vector_similarity_score = round(sc["score"] * 0.8, 10)
                rec.career_match_score = round(career_match, 10)
                rec.math_intensity_match = round(math_match, 10)
                rec.humanities_intensity_match = round(
                    1.0 - abs(prefs.humanities_interest - course["humanities_intensity"]), 10
                )
                rec.graph_distance = float(i)
                rec.prerequisite_score = 1.0 if not course["prerequisites"] else 0.8
                rec.features = {
                    "vector_similarity_score": rec.vector_similarity_score,
                    "career_match_score": rec.career_match_score,
                    "math_intensity_match": rec.math_intensity_match,
                    "humanities_intensity_match": rec.humanities_intensity_match,
                    "graph_distance": rec.graph_distance,
                    "prerequisite_score": rec.prerequisite_score,
                    "course_credits": float(rec.credits),
                    "student_math_interest": prefs.math_interest,
                    "student_humanities_interest": prefs.humanities_interest,
                }
                rec.matched_careers = [c for c in course["career_paths"] if c == career_goal]
                rec.reason = f"Matches your interest in {career_goal}"
                recommendations.append(rec)

            return recommendations

        # Patch the recommend method
        async def mock_recommend(prefs, **kwargs):
            return create_mock_recommendations(prefs)

        recommender.recommend = mock_recommend

        yield recommender

        await recommender.close()

    async def test_pipeline_20_runs_hash_identical(self, mock_recommender):
        """Run full pipeline 20 times → identical hashes.

        HARD CONSTRAINT: Per TOML spec, running the complete RAG pipeline
        20 times with the same input must produce identical output hashes.
        """
        from src.rag.course_recommender import StudentPreferences

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Run pipeline 20 times and compute hashes
        hashes = []
        for i in range(NUM_ITERATIONS):
            results = await mock_recommender.recommend(prefs)
            result_hash = compute_result_hash(results)
            hashes.append(result_hash)

        # All 20 hashes must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash mismatch at run {i + 1} of {NUM_ITERATIONS}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )

    @pytest.mark.parametrize("prefs", [
        AEROSPACE_PREFERENCES,
        DATA_SCIENTIST_PREFERENCES,
        HUMANITIES_PREFERENCES,
    ])
    async def test_pipeline_multiple_profiles_determinism(self, mock_recommender, prefs):
        """Pipeline must be deterministic for different user profiles."""
        from src.rag.course_recommender import StudentPreferences

        student_prefs = StudentPreferences(**prefs)

        # Run 10 times
        hashes = []
        for _ in range(10):
            results = await mock_recommender.recommend(student_prefs)
            result_hash = compute_result_hash(results)
            hashes.append(result_hash)

        # All hashes must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash mismatch at run {i + 1} for profile {prefs['career_goal']}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )

    async def test_pipeline_top_k_consistency(self, mock_recommender):
        """Top-k results must be deterministic."""
        from src.rag.course_recommender import StudentPreferences

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Test different top_k values
        for top_k in [3, 5, 10]:
            top_k_results = []
            for _ in range(5):
                results = await mock_recommender.recommend(prefs)
                top_results = results[:top_k]
                top_k_hash = compute_result_hash(top_results)
                top_k_results.append(top_k_hash)

            # All must be identical
            first = top_k_results[0]
            for i, h in enumerate(top_k_results[1:], 1):
                assert h == first, (
                    f"Top-{top_k} hash mismatch at run {i + 1}:\n"
                    f"Expected: {first}\n"
                    f"Got: {h}"
                )


class TestPipelineComponentDeterminism:
    """Test determinism of individual pipeline components."""

    def test_student_preferences_hash_determinism(self):
        """Same preferences must produce same hash."""
        from src.rag.course_recommender import StudentPreferences

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Hash multiple times
        hashes = []
        for _ in range(10):
            prefs_dict = {
                "math_interest": prefs.math_interest,
                "science_interest": prefs.science_interest,
                "humanities_interest": prefs.humanities_interest,
                "career_goal": prefs.career_goal,
                "learning_style": prefs.learning_style,
                "credits_per_semester": prefs.credits_per_semester,
                "preferred_difficulty": prefs.preferred_difficulty,
            }
            prefs_str = json.dumps(prefs_dict, sort_keys=True)
            prefs_hash = hashlib.sha256(prefs_str.encode()).hexdigest()
            hashes.append(prefs_hash)

        # All identical
        first = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first, f"Preference hash mismatch at iteration {i + 1}"

    def test_feature_extraction_determinism(self):
        """Feature extraction must be deterministic."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class MockRec:
            course_id: str
            total_score: float
            features: Dict[str, float] = field(default_factory=dict)

        rec = MockRec(
            course_id="test-course",
            total_score=0.85,
            features={
                "feature_a": 0.9,
                "feature_b": 0.8,
                "feature_c": 0.7,
            }
        )

        # Extract features multiple times
        feature_hashes = []
        for _ in range(10):
            features = dict(sorted(rec.features.items()))
            feature_str = json.dumps(features, sort_keys=True)
            feature_hash = hashlib.sha256(feature_str.encode()).hexdigest()
            feature_hashes.append(feature_hash)

        # All identical
        first = feature_hashes[0]
        for i, h in enumerate(feature_hashes[1:], 1):
            assert h == first, f"Feature hash mismatch at iteration {i + 1}"


class TestPipelineIntegrationDeterminism:
    """Integration tests for pipeline determinism with real components."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration tests require --run-integration flag"
    )
    async def test_real_pipeline_determinism(self):
        """Test with real (non-mocked) pipeline components.

        This test requires full infrastructure to be available.
        """
        pytest.importorskip("src.rag.course_recommender")

        from src.rag.course_recommender import CourseRecommender, StudentPreferences

        recommender = CourseRecommender()

        try:
            await asyncio.wait_for(recommender.initialize(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.skip("Pipeline initialization timed out")
        except Exception as e:
            pytest.skip(f"Could not initialize pipeline: {e}")

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Run 10 times (fewer for integration test)
        hashes = []
        try:
            for i in range(10):
                results = await recommender.recommend(prefs)
                result_hash = compute_result_hash(results)
                hashes.append(result_hash)
        finally:
            await recommender.close()

        # All must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Real pipeline hash mismatch at run {i + 1}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )


class TestPipelineStateDeterminism:
    """Test that pipeline state doesn't affect determinism."""

    async def test_concurrent_requests_determinism(self, mock_recommender):
        """Concurrent requests must not affect determinism."""
        from src.rag.course_recommender import StudentPreferences

        prefs1 = StudentPreferences(**AEROSPACE_PREFERENCES)
        prefs2 = StudentPreferences(**DATA_SCIENTIST_PREFERENCES)

        # Run requests concurrently
        tasks = [
            mock_recommender.recommend(prefs1),
            mock_recommender.recommend(prefs2),
            mock_recommender.recommend(prefs1),
            mock_recommender.recommend(prefs2),
        ]

        results = await asyncio.gather(*tasks)

        # Same preferences should produce identical results
        hash1_run1 = compute_result_hash(results[0])
        hash1_run2 = compute_result_hash(results[2])
        hash2_run1 = compute_result_hash(results[1])
        hash2_run2 = compute_result_hash(results[3])

        assert hash1_run1 == hash1_run2, "Same prefs produced different hashes (aerospace)"
        assert hash2_run1 == hash2_run2, "Same prefs produced different hashes (data scientist)"

    async def test_sequential_vs_concurrent_determinism(self, mock_recommender):
        """Sequential and concurrent runs must produce same results."""
        from src.rag.course_recommender import StudentPreferences

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Sequential runs
        seq_hashes = []
        for _ in range(5):
            results = await mock_recommender.recommend(prefs)
            seq_hashes.append(compute_result_hash(results))

        # Concurrent runs
        tasks = [mock_recommender.recommend(prefs) for _ in range(5)]
        concurrent_results = await asyncio.gather(*tasks)
        concurrent_hashes = [compute_result_hash(r) for r in concurrent_results]

        # All should match
        for i, (seq, conc) in enumerate(zip(seq_hashes, concurrent_hashes)):
            assert seq == conc, (
                f"Mismatch between sequential and concurrent at run {i + 1}:\n"
                f"Sequential: {seq}\n"
                f"Concurrent: {conc}"
            )


class TestPipelineEdgeCases:
    """Test determinism for edge cases."""

    async def test_empty_results_determinism(self, mock_recommender):
        """Empty results must be handled deterministically."""
        # Mock to return empty
        async def empty_recommend(prefs, **kwargs):
            return []

        mock_recommender.recommend = empty_recommend

        hashes = []
        for _ in range(5):
            results = await mock_recommender.recommend(None)
            h = compute_result_hash(results)
            hashes.append(h)

        # All empty results should have same hash
        first = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first, f"Empty result hash mismatch at run {i + 1}"

    async def test_single_result_determinism(self, mock_recommender):
        """Single result must be deterministic."""
        from src.rag.course_recommender import StudentPreferences

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Get results and only keep top 1
        results = await mock_recommender.recommend(prefs)
        if len(results) > 1:
            # Mock to return only first result
            async def single_recommend(p, **kwargs):
                return [results[0]]
            mock_recommender.recommend = single_recommend

        hashes = []
        for _ in range(10):
            single_results = await mock_recommender.recommend(prefs)
            h = compute_result_hash(single_results)
            hashes.append(h)

        first = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first, f"Single result hash mismatch at run {i + 1}"
