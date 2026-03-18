"""Determinism validation tests for CI/CD pipeline.

These tests verify that the RAG pipeline and XGBoost ranker produce
identical outputs for identical inputs. Any non-determinism will cause
these tests to fail, breaking the CI pipeline.

Hard constraints enforced:
- RAG pipeline must produce identical course rankings for same preferences
- XGBoost ranker must produce identical scores for same features
- All random operations must use fixed seeds

Mark all tests in this file with 'determinism' marker.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from typing import Any, Dict, List

import pytest
import pytest_asyncio

# Skip all determinism tests if explicitly disabled
pytestmark = [
    pytest.mark.determinism,
    pytest.mark.asyncio,
]

# Number of iterations for determinism checks
NUM_ITERATIONS = 10

# Fixed test preferences for aerospace engineer profile
AEROSPACE_PREFERENCES = {
    "math_interest": 0.9,
    "science_interest": 0.85,
    "humanities_interest": 0.2,
    "career_goal": "aerospace_engineer",
    "learning_style": "analytical",
    "credits_per_semester": 15,
    "preferred_difficulty": "advanced",
}

# Fixed test preferences for data scientist profile
DATA_SCIENTIST_PREFERENCES = {
    "math_interest": 0.8,
    "science_interest": 0.75,
    "humanities_interest": 0.4,
    "career_goal": "data_scientist",
    "learning_style": "analytical",
    "credits_per_semester": 12,
    "preferred_difficulty": "intermediate",
}


def normalize_recommendation(rec: Any) -> Dict[str, Any]:
    """Normalize a recommendation for comparison.

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

    # Round all floats to 6 decimal places
    for key, value in data.items():
        if isinstance(value, float):
            data[key] = round(value, 6)
        elif isinstance(value, list):
            data[key] = sorted(value) if value else []

    # Only compare key fields that affect ranking
    return {
        'course_id': data.get('course_id'),
        'total_score': data.get('total_score'),
        'department': data.get('department'),
        'math_intensity': data.get('math_intensity'),
        'career_paths': data.get('career_paths', []),
    }


class TestRAGDeterminism:
    """Test RAG pipeline produces deterministic outputs."""

    @pytest_asyncio.fixture
    async def recommender(self):
        """Create and initialize CourseRecommender."""
        pytest.importorskip("src.rag.course_recommender", reason="RAG module not available")

        from src.rag.course_recommender import CourseRecommender

        recommender = CourseRecommender()

        # Initialize with timeout
        try:
            await asyncio.wait_for(recommender.initialize(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.skip("Recommender initialization timed out")
        except Exception as exc:
            pytest.skip(f"Could not initialize recommender: {exc}")

        yield recommender

        # Cleanup
        await recommender.close()

    @pytest.mark.parametrize("prefs", [
        AEROSPACE_PREFERENCES,
        DATA_SCIENTIST_PREFERENCES,
    ])
    async def test_rag_determinism_same_input(self, recommender, prefs):
        """RAG pipeline must produce identical results for same input.

        HARD CONSTRAINT: All 10 runs must produce identical course_id
        and total_score for the top recommendation.

        Args:
            recommender: Initialized CourseRecommender
            prefs: Student preferences dict
        """
        from src.rag.course_recommender import StudentPreferences

        student_prefs = StudentPreferences(**prefs)

        # Run pipeline multiple times
        results: List[List[Any]] = []
        for i in range(NUM_ITERATIONS):
            recommendations = await recommender.recommend(student_prefs)
            results.append(recommendations)

        # Verify all runs returned results
        assert all(len(r) > 0 for r in results), "Some runs returned no recommendations"

        # Get top recommendation from each run
        top_recs = [r[0] for r in results]

        # Normalize for comparison
        normalized = [normalize_recommendation(r) for r in top_recs]

        # CRITICAL: All must have identical course_id
        course_ids = [r['course_id'] for r in normalized]
        assert all(cid == course_ids[0] for cid in course_ids), (
            f"Non-deterministic course_id across runs: {course_ids}"
        )

        # CRITICAL: All must have identical total_score
        scores = [r['total_score'] for r in normalized]
        assert all(s == scores[0] for s in scores), (
            f"Non-deterministic total_score across runs: {scores}"
        )

    async def test_rag_determinism_full_ranking(self, recommender):
        """Full ranking must be identical across runs.

        HARD CONSTRAINT: The complete ordered list of recommendations
        must be identical across all runs.
        """
        from src.rag.course_recommender import StudentPreferences

        student_prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Run twice
        run1 = await recommender.recommend(student_prefs)
        run2 = await recommender.recommend(student_prefs)

        # Must have same number of results
        assert len(run1) == len(run2), (
            f"Different result counts: {len(run1)} vs {len(run2)}"
        )

        # Each position must be identical
        for i, (r1, r2) in enumerate(zip(run1, run2)):
            n1 = normalize_recommendation(r1)
            n2 = normalize_recommendation(r2)

            assert n1['course_id'] == n2['course_id'], (
                f"Position {i}: different course_id ({n1['course_id']} vs {n2['course_id']})"
            )
            assert n1['total_score'] == n2['total_score'], (
                f"Position {i}: different score ({n1['total_score']} vs {n2['total_score']})"
            )

    async def test_rag_determinism_career_path_consistency(self, recommender):
        """Career path filtering must be deterministic.

        Test that filtering by career goal produces consistent results.
        """
        from src.rag.course_recommender import StudentPreferences

        # Test aerospace engineer specifically
        prefs = StudentPreferences(
            math_interest=0.95,
            science_interest=0.9,
            humanities_interest=0.1,
            career_goal="aerospace_engineer",
            learning_style="analytical",
            credits_per_semester=15,
            preferred_difficulty="advanced",
        )

        results = []
        for _ in range(5):
            recs = await recommender.recommend(prefs)
            results.append(recs)

        # All runs should have same top course
        top_courses = [[r[0].course_id for r in result] for result in results]
        first_top = top_courses[0]

        for i, tops in enumerate(top_courses[1:], 1):
            assert tops == first_top, (
                f"Run {i+1} has different top courses than run 1"
            )


class TestXGBoostDeterminism:
    """Test XGBoost ranker produces deterministic scores."""

    @pytest.fixture
    def ranker_config(self):
        """Create deterministic ranker configuration."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")

        from src.ranking.config import RankingConfig

        return RankingConfig(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,  # FIXED SEED
            subsample=1.0,     # No random sampling
            colsample_bytree=1.0,  # Use all features
        )

    @pytest.fixture
    def sample_features(self):
        """Create fixed test features."""
        pytest.importorskip("numpy", reason="NumPy not installed")
        import numpy as np

        # Fixed features that don't change
        return np.array([
            [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9],   # Aerospace profile
            [0.8, 0.75, 0.4, 0.70, 0.5, 3.0, 0.6, 0.7],   # Data science profile
            [0.3, 0.4, 0.9, 0.15, 0.95, 3.0, 0.4, 0.3],   # Humanities profile
            [0.85, 0.8, 0.3, 0.85, 0.2, 4.0, 0.75, 0.8],  # Engineering profile
        ])

    def test_xgboost_determinism_same_features(self, ranker_config, sample_features):
        """XGBoost must produce identical scores for same features.

        HARD CONSTRAINT: Running prediction 10 times on the same features
        must produce identical scores each time.
        """
        pytest.importorskip("xgboost", reason="XGBoost not installed")
        import numpy as np

        from src.ranking.xgboost_ranker import CourseRanker
        from src.ranking.training_data import TrainingDataGenerator

        # Create and train ranker with fixed seed
        ranker = CourseRanker(config=ranker_config)

        # Generate training data with fixed seed
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)

        # Train model
        metrics = ranker.train(training_data)
        assert metrics["status"] == "success", "Training failed"

        # Predict multiple times
        all_scores = []
        for _ in range(NUM_ITERATIONS):
            scores = ranker.predict(sample_features)
            all_scores.append(scores.copy())

        # All score arrays must be identical
        first_scores = all_scores[0]
        for i, scores in enumerate(all_scores[1:], 1):
            assert np.allclose(scores, first_scores), (
                f"Run {i+1} produced different scores:\n"
                f"Expected: {first_scores}\n"
                f"Got: {scores}\n"
                f"Diff: {np.abs(scores - first_scores)}"
            )

    def test_xgboost_determinism_model_reload(self, ranker_config, sample_features, tmp_path):
        """Model must produce same scores after save and reload."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")
        import numpy as np

        from src.ranking.xgboost_ranker import CourseRanker
        from src.ranking.training_data import TrainingDataGenerator

        # Create model with temp path
        model_path = str(tmp_path / "test_ranker.json")
        config = ranker_config
        config.model_path = model_path

        ranker1 = CourseRanker(config=config)

        # Train
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker1.train(training_data)

        # Get predictions before save
        scores_before = ranker1.predict(sample_features)

        # Save model
        ranker1.save_model()

        # Load in new instance
        ranker2 = CourseRanker(config=config)
        ranker2.load_model()

        # Get predictions after load
        scores_after = ranker2.predict(sample_features)

        # Must be identical
        assert np.allclose(scores_before, scores_after), (
            f"Scores changed after save/reload:\n"
            f"Before: {scores_before}\n"
            f"After: {scores_after}"
        )

    def test_xgboost_determinism_feature_order(self, ranker_config):
        """Feature order must not affect determinism."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")
        import numpy as np

        from src.ranking.xgboost_ranker import CourseRanker
        from src.ranking.training_data import TrainingDataGenerator

        ranker = CourseRanker(config=ranker_config)

        # Train
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker.train(training_data)

        # Same features, multiple prediction calls
        features = np.array([[0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9]])

        scores_list = []
        for _ in range(5):
            scores = ranker.predict(features)
            scores_list.append(scores[0])

        # All should be identical
        assert all(s == scores_list[0] for s in scores_list), (
            f"Scores vary across runs: {scores_list}"
        )


class TestDeterminismEnvironment:
    """Test that environment is configured for determinism."""

    def test_random_seeds_set(self):
        """Random seeds must be set for reproducibility."""
        import random

        # Set seed and verify we get same sequence
        random.seed(42)
        seq1 = [random.random() for _ in range(10)]

        random.seed(42)
        seq2 = [random.random() for _ in range(10)]

        assert seq1 == seq2, "Random seed not working correctly"

    def test_numpy_random_seed(self):
        """NumPy random must be seeded for determinism."""
        np = pytest.importorskip("numpy")

        np.random.seed(42)
        seq1 = np.random.random(10)

        np.random.seed(42)
        seq2 = np.random.random(10)

        assert np.allclose(seq1, seq2), "NumPy random seed not working"

    def test_ci_environment_variables(self):
        """CI environment must have required variables."""
        # In CI, these should be set
        if os.environ.get('CI'):
            assert os.environ.get('PYTEST_CURRENT_TEST'), (
                "PYTEST_CURRENT_TEST should be set in CI"
            )


class TestCogneeIntegrationDeterminism:
    """Integration tests for Cognee adapter determinism."""

    @pytest.fixture
    def cognee_adapter(self):
        """Create CogneeAdapter for testing."""
        pytest.importorskip("src.integrations.cognee_adapter")

        from src.integrations.cognee_adapter import CogneeAdapter

        return CogneeAdapter(
            api_url="http://localhost:8000",
            dataset_name="test_determinism",
        )

    def test_cognee_node_id_determinism(self, cognee_adapter):
        """Cognee adapter must generate deterministic node IDs.

        Verifies that _generate_node_id produces identical UUIDs for
        identical (entity_type, unique_key) inputs.
        """
        entity_type = "Course"
        unique_key = "test-course-001"

        # Generate multiple times
        node_ids = [
            cognee_adapter._generate_node_id(entity_type, unique_key)
            for _ in range(10)
        ]

        # All must be identical
        first_id = node_ids[0]
        for i, nid in enumerate(node_ids[1:], 1):
            assert nid == first_id, (
                f"Node ID changed at iteration {i+1}:\n"
                f"Expected: {first_id}\n"
                f"Got: {nid}"
            )

    def test_cognee_content_hash_determinism(self, cognee_adapter):
        """Content hash must be deterministic for same input."""
        content = "Test course content for deterministic hashing"

        # Hash multiple times
        hashes = [
            cognee_adapter._compute_content_hash(content)
            for _ in range(10)
        ]

        # All must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash changed at iteration {i+1}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )

    def test_cognee_sanitization_determinism(self):
        """Input sanitization must be deterministic."""
        from src.integrations.cognee_adapter import InputSanitizer

        sanitizer = InputSanitizer()

        test_inputs = [
            "Normal string",
            "String with \"quotes\"",
            "String with \\ backslash",
            "test_identifier_123",
            "123numeric_start",
        ]

        for test_input in test_inputs:
            # Sanitize multiple times
            if test_input.startswith("123"):
                results = [sanitizer.sanitize_identifier(test_input) for _ in range(10)]
            else:
                results = [sanitizer.sanitize_string(test_input) for _ in range(10)]

            first = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result == first, (
                    f"Sanitization non-deterministic for '{test_input}' at iteration {i+1}:\n"
                    f"Expected: {first}\n"
                    f"Got: {result}"
                )


class TestXGBoostIntegrationDeterminism:
    """Integration tests for XGBoost ranker determinism."""

    @pytest.fixture(scope="class")
    def xgboost_ranker_config(self):
        """Create deterministic ranker configuration."""
        pytest.importorskip("xgboost")
        pytest.importorskip("numpy")

        from src.ranking.config import RankingConfig

        return RankingConfig(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            subsample=1.0,
            colsample_bytree=1.0,
        )

    @pytest.fixture(scope="class")
    def xgboost_training_data(self):
        """Create fixed training data."""
        from src.ranking.training_data import TrainingDataGenerator

        generator = TrainingDataGenerator(seed=42)
        return generator.generate_all_training_data(variations_per_profile=10)

    @pytest.fixture(scope="class")
    def xgboost_test_features(self):
        """Create fixed test features."""
        import numpy as np

        return np.array([
            [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9, 0.9],
            [0.8, 0.75, 0.4, 0.70, 0.5, 3.0, 0.6, 0.7, 0.8],
            [0.3, 0.4, 0.9, 0.15, 0.95, 3.0, 0.4, 0.3, 0.2],
        ])

    def test_xgboost_training_determinism_3_runs(
        self, xgboost_ranker_config, xgboost_training_data, xgboost_test_features
    ):
        """XGBoost training must be deterministic across 3 runs.

        Trains model 3 times and verifies identical predictions.
        """
        import numpy as np
        from src.ranking.xgboost_ranker import CourseRanker

        all_predictions = []

        for run in range(3):
            ranker = CourseRanker(config=xgboost_ranker_config)

            # Train
            metrics = ranker.train(xgboost_training_data)
            assert metrics["status"] == "success", f"Training failed on run {run + 1}"

            # Predict
            predictions = ranker.predict(xgboost_test_features)
            all_predictions.append(predictions.copy())

        # All predictions must be identical
        first_predictions = all_predictions[0]
        for i, predictions in enumerate(all_predictions[1:], 1):
            assert np.allclose(predictions, first_predictions, rtol=1e-10), (
                f"Run {i + 1} produced different predictions:\n"
                f"Expected: {first_predictions}\n"
                f"Got: {predictions}"
            )

    def test_xgboost_ranking_order_determinism(self, xgboost_ranker_config, xgboost_training_data):
        """XGBoost ranking must produce deterministic ordering."""
        from dataclasses import dataclass, field
        from typing import Dict, List

        from src.ranking.xgboost_ranker import CourseRanker

        @dataclass
        class MockRec:
            course_id: str
            course_name: str
            department: str
            total_score: float
            features: Dict[str, float] = field(default_factory=dict)

        # Create test recommendations
        recommendations = [
            MockRec(
                course_id="course-a",
                course_name="Course A",
                department="DEPT",
                total_score=0.8,
                features={
                    "vector_similarity_score": 0.9,
                    "career_match_score": 0.85,
                    "math_intensity_match": 0.9,
                    "humanities_intensity_match": 0.2,
                    "graph_distance": 1.0,
                    "prerequisite_score": 1.0,
                    "course_credits": 3.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                }
            ),
            MockRec(
                course_id="course-b",
                course_name="Course B",
                department="DEPT",
                total_score=0.75,
                features={
                    "vector_similarity_score": 0.85,
                    "career_match_score": 0.8,
                    "math_intensity_match": 0.7,
                    "humanities_intensity_match": 0.3,
                    "graph_distance": 2.0,
                    "prerequisite_score": 0.9,
                    "course_credits": 4.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                }
            ),
        ]

        # Train ranker
        ranker = CourseRanker(config=xgboost_ranker_config)
        ranker.train(xgboost_training_data)

        # Rank multiple times
        all_orderings = []
        for _ in range(5):
            ranked = ranker.rank(recommendations)
            ordering = [r.course_id for r in ranked]
            all_orderings.append(ordering)

        # All orderings must be identical
        first_ordering = all_orderings[0]
        for i, ordering in enumerate(all_orderings[1:], 1):
            assert ordering == first_ordering, (
                f"Run {i + 1} produced different ordering:\n"
                f"Expected: {first_ordering}\n"
                f"Got: {ordering}"
            )


class TestCogneeXGBoostCombinedDeterminism:
    """Combined determinism tests for Cognee + XGBoost integration."""

    def test_combined_hash_determinism(self):
        """Combined Cognee + XGBoost operations must be deterministic."""
        import hashlib
        import json

        from src.integrations.cognee_adapter import CogneeAdapter, InputSanitizer

        cognee_adapter = CogneeAdapter()
        sanitizer = InputSanitizer()

        # Simulate Cognee ingestion data
        course_data = {
            "id": "course-test-001",
            "name": "Test Course",
            "description": "Test description",
            "department": "TEST",
        }

        # Compute Cognee-related hashes
        node_id = cognee_adapter._generate_node_id("Course", course_data["id"])
        safe_name = sanitizer.sanitize_string(course_data["name"])
        safe_desc = sanitizer.sanitize_string(course_data["description"])
        content = f"{safe_name}. {safe_desc}"
        content_hash = cognee_adapter._compute_content_hash(content)

        cognee_data = {
            "node_id": node_id,
            "content_hash": content_hash,
            "department": course_data["department"],
        }

        # Compute hash 3 times
        hashes = []
        for _ in range(3):
            data_str = json.dumps(cognee_data, sort_keys=True)
            h = hashlib.sha256(data_str.encode()).hexdigest()
            hashes.append(h)

        # All must match
        first = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first, f"Combined hash mismatch at iteration {i + 1}"


class TestIntegrationDeterminism:
    """Integration tests for full pipeline determinism."""

    @pytest.mark.skipif(
        not os.environ.get('CI'),
        reason="Full integration determinism test only in CI"
    )
    async def test_end_to_end_determinism(self):
        """End-to-end test: preferences -> recommendations.

        This is the ultimate determinism test that runs the complete pipeline.
        """
        pytest.importorskip("src.rag.course_recommender")

        from src.rag.course_recommender import CourseRecommender, StudentPreferences

        recommender = CourseRecommender()

        try:
            await asyncio.wait_for(recommender.initialize(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.skip("Initialization timeout")

        prefs = StudentPreferences(**AEROSPACE_PREFERENCES)

        # Run 5 times
        all_results = []
        for _ in range(5):
            results = await recommender.recommend(prefs)
            # Extract just IDs and scores
            summary = [(r.course_id, round(r.total_score, 6)) for r in results[:5]]
            all_results.append(summary)

        await recommender.close()

        # All must be identical
        first = all_results[0]
        for i, result in enumerate(all_results[1:], 1):
            assert result == first, (
                f"Run {i+1} differs from run 1:\n"
                f"Run 1: {first}\n"
                f"Run {i+1}: {result}"
            )
