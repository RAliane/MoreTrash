"""Determinism tests for XGBoost ranking.

These tests validate that the XGBoost ranker produces identical predictions
across multiple runs with the same training data and features.
Per TOML specification:
- Train model 5 times with same data → identical predictions
- Rank same courses 5 times → identical ordering
- Deterministic tie-breaking

Any non-determinism will cause these tests to fail.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Dict, List

import numpy as np
import pytest

# Mark all tests in this file with 'determinism' marker
pytestmark = [
    pytest.mark.determinism,
]

# Fixed seeds per TOML specification
RANKER_SEED = 42
NUM_ITERATIONS = 5


class TestXGBoostTrainingDeterminism:
    """Test XGBoost model training determinism."""

    @pytest.fixture(scope="class")
    def ranker_config(self):
        """Create deterministic ranker configuration."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")
        pytest.importorskip("numpy", reason="NumPy not installed")

        from src.ranking.config import RankingConfig

        return RankingConfig(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            random_state=RANKER_SEED,
            subsample=1.0,  # No random sampling
            colsample_bytree=1.0,  # Use all features
            model_path="/tmp/test_ranker_determinism.json",
        )

    @pytest.fixture(scope="class")
    def training_data(self):
        """Create fixed training data."""
        pytest.importorskip("src.ranking.training_data", reason="Training data module not available")

        from src.ranking.training_data import TrainingDataGenerator

        # Use fixed seed for deterministic data generation
        generator = TrainingDataGenerator(seed=RANKER_SEED)
        return generator.generate_all_training_data(variations_per_profile=10)

    @pytest.fixture(scope="class")
    def sample_features(self):
        """Create fixed test features for prediction."""
        return np.array([
            [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9, 0.9],   # Aerospace profile
            [0.8, 0.75, 0.4, 0.70, 0.5, 3.0, 0.6, 0.7, 0.8],   # Data science profile
            [0.3, 0.4, 0.9, 0.15, 0.95, 3.0, 0.4, 0.3, 0.2],   # Humanities profile
            [0.85, 0.8, 0.3, 0.85, 0.2, 4.0, 0.75, 0.8, 0.85],  # Engineering profile
            [0.5, 0.6, 0.5, 0.5, 0.5, 3.0, 0.5, 0.5, 0.5],      # Balanced profile
        ])

    def test_training_determinism_5_runs(self, ranker_config, training_data, sample_features):
        """Train model 5 times → identical predictions.

        HARD CONSTRAINT: Per TOML spec, training with same data and seed
        must produce models that give identical predictions.
        """
        from src.ranking.xgboost_ranker import CourseRanker

        # Train and predict 5 times
        all_predictions = []
        for run in range(NUM_ITERATIONS):
            # Create fresh ranker
            ranker = CourseRanker(config=ranker_config)

            # Train
            metrics = ranker.train(training_data)
            assert metrics["status"] == "success", f"Training failed on run {run + 1}"

            # Predict
            predictions = ranker.predict(sample_features)
            all_predictions.append(predictions.copy())

        # All prediction arrays must be identical
        first_predictions = all_predictions[0]
        for i, predictions in enumerate(all_predictions[1:], 1):
            assert np.allclose(predictions, first_predictions, rtol=1e-10, atol=1e-10), (
                f"Run {i + 1} produced different predictions:\n"
                f"Expected: {first_predictions}\n"
                f"Got: {predictions}\n"
                f"Diff: {np.abs(predictions - first_predictions)}"
            )

    def test_training_feature_importance_determinism(self, ranker_config, training_data):
        """Feature importance must be identical across training runs."""
        from src.ranking.xgboost_ranker import CourseRanker

        # Train twice
        ranker1 = CourseRanker(config=ranker_config)
        ranker1.train(training_data)
        importance1 = ranker1.get_feature_importance()

        ranker2 = CourseRanker(config=ranker_config)
        ranker2.train(training_data)
        importance2 = ranker2.get_feature_importance()

        # Compare feature importance
        assert set(importance1.keys()) == set(importance2.keys()), (
            "Feature importance keys differ between runs"
        )

        for feature in importance1.keys():
            assert np.isclose(importance1[feature], importance2[feature], rtol=1e-10), (
                f"Feature importance for '{feature}' differs:\n"
                f"Run 1: {importance1[feature]}\n"
                f"Run 2: {importance2[feature]}"
            )


class TestXGBoostRankingDeterminism:
    """Test XGBoost ranking determinism with CourseRecommendations."""

    @pytest.fixture
    def sample_recommendations(self):
        """Create deterministic sample recommendations."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class MockRecommendation:
            course_id: str
            course_name: str
            department: str
            description: str = "Test description"
            career_paths: List[str] = field(default_factory=list)
            credits: int = 3
            math_intensity: float = 0.5
            humanities_intensity: float = 0.5
            total_score: float = 0.0
            vector_similarity_score: float = 0.0
            career_match_score: float = 0.0
            math_intensity_match: float = 0.0
            humanities_intensity_match: float = 0.0
            graph_distance: float = 0.0
            prerequisite_score: float = 0.0
            features: Dict[str, float] = field(default_factory=dict)

        return [
            MockRecommendation(
                course_id="course-math-101",
                course_name="Mathematics 101",
                department="MATH",
                career_paths=["data_scientist", "engineer"],
                total_score=0.85,
                features={
                    "vector_similarity_score": 0.9,
                    "career_match_score": 0.85,
                    "math_intensity_match": 0.95,
                    "humanities_intensity_match": 0.1,
                    "graph_distance": 1.0,
                    "prerequisite_score": 1.0,
                    "course_credits": 3.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                }
            ),
            MockRecommendation(
                course_id="course-cs-101",
                course_name="Computer Science 101",
                department="CS",
                career_paths=["software_engineer"],
                total_score=0.82,
                features={
                    "vector_similarity_score": 0.85,
                    "career_match_score": 0.8,
                    "math_intensity_match": 0.7,
                    "humanities_intensity_match": 0.2,
                    "graph_distance": 2.0,
                    "prerequisite_score": 0.9,
                    "course_credits": 4.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                }
            ),
            MockRecommendation(
                course_id="course-phys-101",
                course_name="Physics 101",
                department="PHYS",
                career_paths=["engineer", "scientist"],
                total_score=0.78,
                features={
                    "vector_similarity_score": 0.8,
                    "career_match_score": 0.75,
                    "math_intensity_match": 0.85,
                    "humanities_intensity_match": 0.15,
                    "graph_distance": 1.5,
                    "prerequisite_score": 0.85,
                    "course_credits": 4.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                }
            ),
        ]

    @pytest.fixture
    def trained_ranker(self):
        """Create and train a ranker for ranking tests."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")

        from src.ranking.config import RankingConfig
        from src.ranking.training_data import TrainingDataGenerator
        from src.ranking.xgboost_ranker import CourseRanker

        config = RankingConfig(
            n_estimators=30,
            max_depth=3,
            learning_rate=0.1,
            random_state=RANKER_SEED,
            subsample=1.0,
            colsample_bytree=1.0,
        )

        ranker = CourseRanker(config=config)

        # Generate and train with fixed seed
        generator = TrainingDataGenerator(seed=RANKER_SEED)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker.train(training_data)

        return ranker

    def test_ranking_order_determinism(self, trained_ranker, sample_recommendations):
        """Rank same courses 5 times → identical ordering.

        HARD CONSTRAINT: Per TOML spec, ranking the same courses
        must produce identical ordering across multiple runs.
        """
        # Rank multiple times
        all_orderings = []
        for _ in range(NUM_ITERATIONS):
            ranked = trained_ranker.rank(sample_recommendations)
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

    def test_ranking_scores_determinism(self, trained_ranker, sample_recommendations):
        """Rank scores must be identical across runs."""
        # Rank multiple times
        all_scores = []
        for _ in range(NUM_ITERATIONS):
            ranked = trained_ranker.rank(sample_recommendations)
            scores = [(r.course_id, round(r.total_score, 10)) for r in ranked]
            all_scores.append(scores)

        # All scores must be identical
        first_scores = all_scores[0]
        for i, scores in enumerate(all_scores[1:], 1):
            assert scores == first_scores, (
                f"Run {i + 1} produced different scores:\n"
                f"Expected: {first_scores}\n"
                f"Got: {scores}"
            )

    def test_tie_breaking_determinism(self, trained_ranker):
        """Tie-breaking must be deterministic (course_id ASC)."""
        from dataclasses import dataclass, field
        from typing import List

        @dataclass
        class MockRecommendation:
            course_id: str
            course_name: str
            department: str
            description: str = "Test"
            career_paths: List[str] = field(default_factory=list)
            credits: int = 3
            math_intensity: float = 0.5
            humanities_intensity: float = 0.5
            total_score: float = 0.0
            vector_similarity_score: float = 0.0
            career_match_score: float = 0.0
            math_intensity_match: float = 0.0
            humanities_intensity_match: float = 0.0
            graph_distance: float = 0.0
            prerequisite_score: float = 0.0
            features: Dict[str, float] = field(default_factory=dict)

        # Create recommendations with identical scores (to test tie-breaking)
        recommendations = [
            MockRecommendation(
                course_id="course-c",
                course_name="Course C",
                department="DEPT",
                total_score=0.75,
                features={"vector_similarity_score": 0.5, "career_match_score": 0.5,
                         "math_intensity_match": 0.5, "humanities_intensity_match": 0.5,
                         "graph_distance": 1.0, "prerequisite_score": 0.5,
                         "course_credits": 3.0, "student_math_interest": 0.5,
                         "student_humanities_interest": 0.5},
            ),
            MockRecommendation(
                course_id="course-a",
                course_name="Course A",
                department="DEPT",
                total_score=0.75,  # Same score
                features={"vector_similarity_score": 0.5, "career_match_score": 0.5,
                         "math_intensity_match": 0.5, "humanities_intensity_match": 0.5,
                         "graph_distance": 1.0, "prerequisite_score": 0.5,
                         "course_credits": 3.0, "student_math_interest": 0.5,
                         "student_humanities_interest": 0.5},
            ),
            MockRecommendation(
                course_id="course-b",
                course_name="Course B",
                department="DEPT",
                total_score=0.75,  # Same score
                features={"vector_similarity_score": 0.5, "career_match_score": 0.5,
                         "math_intensity_match": 0.5, "humanities_intensity_match": 0.5,
                         "graph_distance": 1.0, "prerequisite_score": 0.5,
                         "course_credits": 3.0, "student_math_interest": 0.5,
                         "student_humanities_interest": 0.5},
            ),
        ]

        # Rank multiple times
        all_orderings = []
        for _ in range(10):
            ranked = trained_ranker.rank(recommendations)
            ordering = [r.course_id for r in ranked]
            all_orderings.append(ordering)

        # All orderings must be identical (deterministic tie-breaking)
        first_ordering = all_orderings[0]
        for i, ordering in enumerate(all_orderings[1:], 1):
            assert ordering == first_ordering, (
                f"Run {i + 1} produced different tie-breaking:\n"
                f"Expected: {first_ordering}\n"
                f"Got: {ordering}"
            )

        # Verify alphabetical ordering for ties
        # (score DESC, course_id ASC)
        assert first_ordering == sorted(first_ordering), (
            f"Tie-breaking not alphabetical: {first_ordering}"
        )


class TestXGBoostModelPersistence:
    """Test model save/load determinism."""

    def test_model_save_load_determinism(self, tmp_path):
        """Model must produce same predictions after save and reload."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")

        from src.ranking.config import RankingConfig
        from src.ranking.training_data import TrainingDataGenerator
        from src.ranking.xgboost_ranker import CourseRanker

        # Fixed test features
        test_features = np.array([
            [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9, 0.9],
            [0.8, 0.75, 0.4, 0.70, 0.5, 3.0, 0.6, 0.7, 0.8],
        ])

        model_path = str(tmp_path / "test_model.json")

        config = RankingConfig(
            n_estimators=30,
            max_depth=3,
            learning_rate=0.1,
            random_state=RANKER_SEED,
            subsample=1.0,
            colsample_bytree=1.0,
            model_path=model_path,
        )

        # Create and train first ranker
        ranker1 = CourseRanker(config=config)
        generator = TrainingDataGenerator(seed=RANKER_SEED)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker1.train(training_data)

        # Get predictions before save
        scores_before = ranker1.predict(test_features)

        # Save model
        ranker1.save_model()

        # Create new ranker and load
        ranker2 = CourseRanker(config=config)
        ranker2.load_model()

        # Get predictions after load
        scores_after = ranker2.predict(test_features)

        # Must be identical
        assert np.allclose(scores_before, scores_after, rtol=1e-10, atol=1e-10), (
            f"Predictions changed after save/reload:\n"
            f"Before: {scores_before}\n"
            f"After: {scores_after}\n"
            f"Diff: {np.abs(scores_before - scores_after)}"
        )


class TestXGBoostHashValidation:
    """Test determinism using hash comparisons."""

    def test_prediction_hash_consistency(self):
        """Prediction hashes must be identical across runs."""
        pytest.importorskip("xgboost", reason="XGBoost not installed")

        from src.ranking.config import RankingConfig
        from src.ranking.training_data import TrainingDataGenerator
        from src.ranking.xgboost_ranker import CourseRanker

        # Fixed features
        features = np.array([
            [0.9, 0.85, 0.2, 0.95, 0.1, 4.0, 0.8, 0.9, 0.9],
            [0.8, 0.75, 0.4, 0.70, 0.5, 3.0, 0.6, 0.7, 0.8],
            [0.3, 0.4, 0.9, 0.15, 0.95, 3.0, 0.4, 0.3, 0.2],
        ])

        config = RankingConfig(
            n_estimators=30,
            max_depth=3,
            learning_rate=0.1,
            random_state=RANKER_SEED,
            subsample=1.0,
            colsample_bytree=1.0,
        )

        # Train and hash predictions 3 times
        hashes = []
        for _ in range(3):
            ranker = CourseRanker(config=config)
            generator = TrainingDataGenerator(seed=RANKER_SEED)
            training_data = generator.generate_all_training_data(variations_per_profile=5)
            ranker.train(training_data)

            predictions = ranker.predict(features)

            # Create deterministic hash
            pred_dict = {
                "predictions": [round(float(p), 10) for p in predictions],
                "shape": predictions.shape,
            }
            pred_str = json.dumps(pred_dict, sort_keys=True)
            pred_hash = hashlib.sha256(pred_str.encode()).hexdigest()
            hashes.append(pred_hash)

        # All hashes must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash mismatch at run {i + 1}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )


class TestXGBoostFallbackDeterminism:
    """Test determinism when XGBoost is not available (fallback mode)."""

    def test_fallback_ranking_determinism(self, sample_recommendations):
        """Fallback ranking must still be deterministic."""
        from src.ranking.config import RankingConfig
        from src.ranking.xgboost_ranker import CourseRanker

        config = RankingConfig(
            n_estimators=10,
            max_depth=2,
            random_state=RANKER_SEED,
        )

        ranker = CourseRanker(config=config)
        # Model is not trained, will use fallback

        # Rank multiple times
        all_orderings = []
        for _ in range(5):
            ranked = ranker.rank(sample_recommendations)
            ordering = [r.course_id for r in ranked]
            all_orderings.append(ordering)

        # All orderings must be identical
        first_ordering = all_orderings[0]
        for i, ordering in enumerate(all_orderings[1:], 1):
            assert ordering == first_ordering, (
                f"Fallback run {i + 1} produced different ordering:\n"
                f"Expected: {first_ordering}\n"
                f"Got: {ordering}"
            )


class TestXGBoostRandomSeed:
    """Test that random seeds are properly set."""

    def test_numpy_random_seed_determinism(self):
        """NumPy random operations must be deterministic."""
        sequences = []
        for _ in range(3):
            np.random.seed(RANKER_SEED)
            seq = np.random.random(10)
            sequences.append(seq)

        first_seq = sequences[0]
        for i, seq in enumerate(sequences[1:], 1):
            assert np.allclose(seq, first_seq), (
                f"NumPy random sequence differs at run {i + 1}"
            )

    def test_python_random_seed_determinism(self):
        """Python random operations must be deterministic."""
        sequences = []
        for _ in range(3):
            random.seed(RANKER_SEED)
            seq = [random.random() for _ in range(10)]
            sequences.append(seq)

        first_seq = sequences[0]
        for i, seq in enumerate(sequences[1:], 1):
            assert seq == first_seq, (
                f"Python random sequence differs at run {i + 1}"
            )

    def test_ranking_config_random_state(self):
        """RankingConfig must use fixed random state."""
        from src.ranking.config import RankingConfig, RANKER_RANDOM_STATE

        config = RankingConfig()
        assert config.random_state == RANKER_RANDOM_STATE, (
            f"Random state not using fixed value: {config.random_state} != {RANKER_RANDOM_STATE}"
        )
