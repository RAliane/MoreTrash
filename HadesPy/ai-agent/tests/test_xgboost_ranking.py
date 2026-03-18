"""Tests for XGBoost ranking integration.

Validates the learning-to-rank functionality including:
- Ranking correctness for different student profiles
- Deterministic output for same inputs
- Score monotonicity
- Feature importance
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import List

import pytest
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ranking.config import RankingConfig, get_ranking_config
from src.ranking.training_data import (
    TrainingDataGenerator,
    TrainingExample,
    STUDENT_PROFILES,
    COURSE_CATALOG,
    generate_training_data,
)
from src.ranking.xgboost_ranker import CourseRanker
from src.rag.course_recommender import (
    CourseRecommendation,
    CourseRecommender,
    StudentPreferences,
)

# Skip all tests if XGBoost is not available
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not XGBOOST_AVAILABLE,
    reason="XGBoost not installed"
)


@pytest.fixture
def temp_model_dir():
    """Create a temporary directory for model files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config(temp_model_dir):
    """Create a test configuration."""
    return RankingConfig(
        model_path=os.path.join(temp_model_dir, "ranker.json"),
        training_data_path=os.path.join(temp_model_dir, "training_data.jsonl"),
        n_estimators=50,  # Smaller for faster tests
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
    )


@pytest.fixture
def trained_ranker(config):
    """Create and train a ranker with synthetic data."""
    ranker = CourseRanker(model_path=config.model_path, config=config)
    
    # Generate training data
    generator = TrainingDataGenerator(seed=42)
    training_data = generator.generate_all_training_data(variations_per_profile=10)
    
    # Train model
    metrics = ranker.train(training_data)
    assert metrics["status"] == "success"
    
    return ranker


@pytest.fixture
def sample_recommendations() -> List[CourseRecommendation]:
    """Create sample recommendations for testing."""
    return [
        CourseRecommendation(
            course_id="aerospace_eng",
            course_name="Aerospace Engineering",
            department="ENG",
            description="Study of aircraft and spacecraft",
            career_paths=["aerospace_engineer"],
            credits=4,
            math_intensity=0.95,
            humanities_intensity=0.1,
            total_score=0.85,
            vector_similarity_score=0.8,
            career_match_score=1.0,
            math_intensity_match=0.95,
            humanities_intensity_match=0.7,
            graph_distance=1.0,
            prerequisite_score=1.0,
            features={
                "vector_similarity_score": 0.8,
                "career_match_score": 1.0,
                "math_intensity_match": 0.95,
                "humanities_intensity_match": 0.7,
                "graph_distance": 1.0,
                "prerequisite_score": 1.0,
                "course_credits": 4.0,
                "student_math_interest": 0.9,
                "student_humanities_interest": 0.2,
            },
        ),
        CourseRecommendation(
            course_id="computer_science",
            course_name="Computer Science",
            department="CS",
            description="Study of computation and programming",
            career_paths=["software_engineer"],
            credits=4,
            math_intensity=0.8,
            humanities_intensity=0.2,
            total_score=0.75,
            vector_similarity_score=0.75,
            career_match_score=0.0,
            math_intensity_match=0.85,
            humanities_intensity_match=0.8,
            graph_distance=2.0,
            prerequisite_score=1.0,
            features={
                "vector_similarity_score": 0.75,
                "career_match_score": 0.0,
                "math_intensity_match": 0.85,
                "humanities_intensity_match": 0.8,
                "graph_distance": 2.0,
                "prerequisite_score": 1.0,
                "course_credits": 4.0,
                "student_math_interest": 0.9,
                "student_humanities_interest": 0.2,
            },
        ),
        CourseRecommendation(
            course_id="philosophy",
            course_name="Philosophy",
            department="HUM",
            description="Study of fundamental questions",
            career_paths=["philosopher"],
            credits=3,
            math_intensity=0.2,
            humanities_intensity=0.95,
            total_score=0.45,
            vector_similarity_score=0.5,
            career_match_score=0.0,
            math_intensity_match=0.65,
            humanities_intensity_match=0.85,
            graph_distance=3.0,
            prerequisite_score=1.0,
            features={
                "vector_similarity_score": 0.5,
                "career_match_score": 0.0,
                "math_intensity_match": 0.65,
                "humanities_intensity_match": 0.85,
                "graph_distance": 3.0,
                "prerequisite_score": 1.0,
                "course_credits": 3.0,
                "student_math_interest": 0.9,
                "student_humanities_interest": 0.2,
            },
        ),
    ]


class TestCourseRanker:
    """Tests for the CourseRanker class."""
    
    def test_initialization(self, config):
        """Test ranker initialization."""
        ranker = CourseRanker(model_path=config.model_path, config=config)
        assert ranker.model_path == config.model_path
        assert not ranker.is_trained
        assert len(ranker.feature_names) == 9
    
    def test_train_model(self, config):
        """Test model training."""
        ranker = CourseRanker(model_path=config.model_path, config=config)
        
        # Generate training data
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        
        # Train
        metrics = ranker.train(training_data)
        
        assert metrics["status"] == "success"
        assert metrics["num_training_samples"] > 0
        assert metrics["num_features"] == 9
        assert ranker.is_trained
    
    def test_model_persistence(self, config):
        """Test model saving and loading."""
        ranker1 = CourseRanker(model_path=config.model_path, config=config)
        
        # Generate and train
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker1.train(training_data)
        
        # Create new ranker that should load the saved model
        ranker2 = CourseRanker(model_path=config.model_path, config=config)
        assert ranker2.is_trained
    
    def test_ranking(self, trained_ranker, sample_recommendations):
        """Test ranking produces valid output."""
        reranked = trained_ranker.rank(sample_recommendations)
        
        assert len(reranked) == len(sample_recommendations)
        
        # Check that xgboost_score was added
        for rec in reranked:
            assert "xgboost_score" in rec.features
    
    def test_deterministic_ranking(self, trained_ranker, sample_recommendations):
        """Test that ranking is deterministic."""
        results = []
        for _ in range(10):
            reranked = trained_ranker.rank(sample_recommendations)
            results.append([r.course_id for r in reranked])
        
        # All results should be identical
        first = results[0]
        assert all(r == first for r in results)
    
    def test_score_monotonicity(self, trained_ranker):
        """Test that higher scores result in better rankings."""
        # Create recommendations with clearly different quality
        high_quality = CourseRecommendation(
            course_id="high",
            course_name="High Quality Course",
            department="ENG",
            description="Best course",
            career_paths=["engineer"],
            credits=4,
            math_intensity=0.9,
            humanities_intensity=0.2,
            features={
                "vector_similarity_score": 0.95,
                "career_match_score": 1.0,
                "math_intensity_match": 0.95,
                "humanities_intensity_match": 0.9,
                "graph_distance": 0.5,
                "prerequisite_score": 1.0,
                "course_credits": 4.0,
                "student_math_interest": 0.9,
                "student_humanities_interest": 0.2,
            },
        )
        
        low_quality = CourseRecommendation(
            course_id="low",
            course_name="Low Quality Course",
            department="HUM",
            description="Worst course",
            career_paths=["writer"],
            credits=3,
            math_intensity=0.2,
            humanities_intensity=0.9,
            features={
                "vector_similarity_score": 0.3,
                "career_match_score": 0.0,
                "math_intensity_match": 0.3,
                "humanities_intensity_match": 0.3,
                "graph_distance": 4.0,
                "prerequisite_score": 0.5,
                "course_credits": 3.0,
                "student_math_interest": 0.9,
                "student_humanities_interest": 0.2,
            },
        )
        
        recommendations = [low_quality, high_quality]
        reranked = trained_ranker.rank(recommendations)
        
        # High quality should be ranked first
        assert reranked[0].course_id == "high"
        assert reranked[1].course_id == "low"
    
    def test_feature_importance(self, trained_ranker):
        """Test feature importance extraction."""
        importance = trained_ranker.get_feature_importance()
        
        assert len(importance) > 0
        # Importance should sum to 1 (normalized)
        total = sum(importance.values())
        assert abs(total - 1.0) < 0.01
    
    def test_evaluate(self, trained_ranker):
        """Test model evaluation."""
        generator = TrainingDataGenerator(seed=123)
        test_data = generator.generate_all_training_data(variations_per_profile=3)
        
        metrics = trained_ranker.evaluate(test_data, k=5)
        
        assert "ndcg@5" in metrics
        assert 0 <= metrics["ndcg@5"] <= 1


class TestAerospaceRanking:
    """Tests specific to aerospace engineer preference profile."""
    
    @pytest.mark.asyncio
    async def test_aerospace_ranking_first(self, trained_ranker):
        """Aerospace preference should rank Aerospace Engineering first."""
        # Create aerospace-optimized recommendations
        recommendations = [
            CourseRecommendation(
                course_id="aerospace_eng",
                course_name="Aerospace Engineering",
                department="ENG",
                description="Aircraft and spacecraft",
                career_paths=["aerospace_engineer"],
                credits=4,
                math_intensity=0.95,
                humanities_intensity=0.1,
                features={
                    "vector_similarity_score": 0.85,
                    "career_match_score": 1.0,
                    "math_intensity_match": 0.95,
                    "humanities_intensity_match": 0.75,
                    "graph_distance": 1.0,
                    "prerequisite_score": 1.0,
                    "course_credits": 4.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                },
            ),
            CourseRecommendation(
                course_id="philosophy",
                course_name="Philosophy",
                department="HUM",
                description="Philosophy course",
                career_paths=["philosopher"],
                credits=3,
                math_intensity=0.2,
                humanities_intensity=0.95,
                features={
                    "vector_similarity_score": 0.5,
                    "career_match_score": 0.0,
                    "math_intensity_match": 0.5,
                    "humanities_intensity_match": 0.9,
                    "graph_distance": 3.0,
                    "prerequisite_score": 1.0,
                    "course_credits": 3.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                },
            ),
            CourseRecommendation(
                course_id="mechanical_eng",
                course_name="Mechanical Engineering",
                department="ENG",
                description="Mechanical systems",
                career_paths=["mechanical_engineer", "aerospace_engineer"],
                credits=4,
                math_intensity=0.85,
                humanities_intensity=0.15,
                features={
                    "vector_similarity_score": 0.75,
                    "career_match_score": 0.5,
                    "math_intensity_match": 0.85,
                    "humanities_intensity_match": 0.7,
                    "graph_distance": 1.5,
                    "prerequisite_score": 1.0,
                    "course_credits": 4.0,
                    "student_math_interest": 0.9,
                    "student_humanities_interest": 0.2,
                },
            ),
        ]
        
        reranked = trained_ranker.rank(recommendations)
        
        # Aerospace Engineering should be ranked first
        assert reranked[0].course_id == "aerospace_eng"


class TestTrainingDataGenerator:
    """Tests for the TrainingDataGenerator."""
    
    def test_generate_single_example(self):
        """Test generating a single training example."""
        generator = TrainingDataGenerator(seed=42)
        
        example = generator.generate_training_example(
            profile_name="aerospace_engineer",
            course_id="aerospace_eng",
            position=0,
            query_id="test_query",
            add_noise=False,
        )
        
        assert isinstance(example, TrainingExample)
        assert example.query_id == "test_query"
        assert example.course_id == "aerospace_eng"
        assert example.relevance_score == 5  # Position 0 = relevance 5
        assert "vector_similarity_score" in example.features
    
    def test_generate_profile_examples(self):
        """Test generating examples for a profile."""
        generator = TrainingDataGenerator(seed=42)
        
        examples = generator.generate_profile_examples(
            profile_name="aerospace_engineer",
            num_variations=5,
        )
        
        # 5 variations * 5 courses = 25 examples
        assert len(examples) == 25
        
        # Check all courses are represented
        course_ids = set(ex.course_id for ex in examples)
        assert len(course_ids) == 5
    
    def test_save_and_load(self, temp_model_dir):
        """Test saving and loading training data."""
        generator = TrainingDataGenerator(seed=42)
        examples = generator.generate_profile_examples(
            profile_name="aerospace_engineer",
            num_variations=3,
        )
        
        output_path = os.path.join(temp_model_dir, "test_data.jsonl")
        generator.save_training_data(examples, output_path)
        
        loaded = generator.load_training_data(output_path)
        assert len(loaded) == len(examples)
    
    def test_statistics(self):
        """Test statistics generation."""
        generator = TrainingDataGenerator(seed=42)
        examples = generator.generate_all_training_data(variations_per_profile=5)
        
        stats = generator.get_statistics(examples)
        
        assert stats["total_examples"] == 150  # 6 profiles * 5 variations * 5 courses
        assert stats["unique_queries"] == 30  # 6 profiles * 5 variations
        assert len(stats["feature_means"]) == 9


class TestIntegration:
    """Integration tests with CourseRecommender."""
    
    @pytest.mark.asyncio
    async def test_recommend_with_xgboost(self, config, temp_model_dir):
        """Test full recommendation pipeline with XGBoost."""
        # This test requires a mock or stub for the graph/vector store
        # For now, we just verify the XGBoost ranker is initialized correctly
        
        # Train a model first
        ranker = CourseRanker(model_path=config.model_path, config=config)
        generator = TrainingDataGenerator(seed=42)
        training_data = generator.generate_all_training_data(variations_per_profile=5)
        ranker.train(training_data)
        
        # Create recommender with XGBoost enabled
        recommender = CourseRecommender(
            use_xgboost_ranking=True,
            xgboost_ranker=ranker,
        )
        
        assert recommender.use_xgboost_ranking is True
        assert recommender.xgboost_ranker is not None
        assert recommender.xgboost_ranker.is_trained


def test_feature_names_match():
    """Test that feature names in config match training data."""
    config = get_ranking_config()
    
    # Generate example and check features
    generator = TrainingDataGenerator(seed=42)
    example = generator.generate_training_example(
        profile_name="aerospace_engineer",
        course_id="aerospace_eng",
        position=0,
        query_id="test",
    )
    
    # All config features should be present in the example
    for feature_name in config.feature_names:
        assert feature_name in example.features, f"Missing feature: {feature_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
