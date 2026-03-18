#!/usr/bin/env python3
"""CLI tool for training and evaluating the XGBoost ranker.

Commands:
    --generate-data: Generate synthetic training data
    --train: Train the XGBoost model
    --evaluate: Evaluate model performance
    --rank: Test ranking with sample preferences
    --info: Show model information

Examples:
    python scripts/train_ranker.py --generate-data
    python scripts/train_ranker.py --train --variations 30
    python scripts/train_ranker.py --evaluate
    python scripts/train_ranker.py --rank --student-prefs '{"math_interest": 0.9, "career_goal": "aerospace_engineer"}'
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from src.ranking.config import get_ranking_config, RankingConfig
from src.ranking.training_data import (
    TrainingDataGenerator,
    generate_training_data,
    STUDENT_PROFILES,
    COURSE_CATALOG,
)
from src.ranking.xgboost_ranker import CourseRanker
from src.rag.course_recommender import CourseRecommendation
from src.logging_config import get_logger

logger = get_logger(__name__)


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{title}")
    print("-" * len(title))


def cmd_generate_data(args: argparse.Namespace) -> int:
    """Generate synthetic training data.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print_header("GENERATING TRAINING DATA")
    
    print(f"Variations per profile: {args.variations}")
    print(f"Random seed: {args.seed}")
    
    output_path = generate_training_data(
        variations_per_profile=args.variations,
        seed=args.seed,
    )
    
    # Load and display statistics
    generator = TrainingDataGenerator(seed=args.seed)
    examples = generator.load_training_data(output_path)
    stats = generator.get_statistics(examples)
    
    print_section("Training Data Statistics")
    print(f"Total examples: {stats['total_examples']}")
    print(f"Unique queries: {stats['unique_queries']}")
    print(f"Unique courses: {stats['unique_courses']}")
    print(f"Examples per query: {stats['examples_per_query']:.1f}")
    
    print_section("Relevance Distribution")
    for score, count in sorted(stats['relevance_distribution'].items()):
        pct = 100 * count / stats['total_examples']
        print(f"  Relevance {score}: {count:4d} ({pct:5.1f}%)")
    
    print_section("Course Distribution")
    for course_id, count in sorted(stats['course_distribution'].items()):
        print(f"  {course_id}: {count}")
    
    print_section("Profile Distribution")
    for profile, count in sorted(stats['profile_distribution'].items()):
        print(f"  {profile}: {count}")
    
    print_section("Feature Means")
    for feature, mean in sorted(stats['feature_means'].items()):
        print(f"  {feature}: {mean:.3f}")
    
    print(f"\nTraining data saved to: {output_path}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    """Train the XGBoost model.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print_header("TRAINING XGBOOST RANKER")
    
    # Get or create config
    config = get_ranking_config()
    if args.model_path:
        config.model_path = args.model_path
    
    print(f"Model path: {config.model_path}")
    print(f"Objective: {config.objective}")
    print(f"N_estimators: {config.n_estimators}")
    print(f"Max_depth: {config.max_depth}")
    print(f"Learning_rate: {config.learning_rate}")
    print(f"Random_state: {config.random_state}")
    
    # Initialize ranker
    ranker = CourseRanker(model_path=config.model_path, config=config)
    
    # Check for existing training data
    generator = TrainingDataGenerator(seed=args.seed)
    training_data = None
    
    if os.path.exists(config.training_data_path):
        print(f"\nLoading existing training data from: {config.training_data_path}")
        training_data = generator.load_training_data(config.training_data_path)
    else:
        print(f"\nNo existing training data found. Generating with {args.variations} variations...")
        training_data = generator.generate_all_training_data(
            variations_per_profile=args.variations
        )
        generator.save_training_data(training_data)
    
    print(f"Training examples: {len(training_data)}")
    
    # Train model
    print("\nTraining model...")
    metrics = ranker.train(training_data)
    
    if metrics["status"] != "success":
        print(f"ERROR: Training failed - {metrics.get('error', 'Unknown error')}")
        return 1
    
    print_section("Training Results")
    print(f"Training samples: {metrics['num_training_samples']}")
    print(f"Validation samples: {metrics['num_validation_samples']}")
    print(f"Features: {metrics['num_features']}")
    print(f"Training score mean: {metrics['training_score_mean']:.4f}")
    print(f"Validation score mean: {metrics['validation_score_mean']:.4f}")
    
    print_section("Feature Importance")
    importance = metrics.get("feature_importance", {})
    for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(score * 50)
        print(f"  {feature:35s} {score:.3f} {bar}")
    
    print(f"\nModel saved to: {config.model_path}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate the model.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print_header("EVALUATING XGBOOST RANKER")
    
    config = get_ranking_config()
    if args.model_path:
        config.model_path = args.model_path
    
    # Initialize ranker
    ranker = CourseRanker(model_path=config.model_path, config=config)
    
    if not ranker.is_trained:
        print("ERROR: Model not found or not trained.")
        print(f"Run: python scripts/train_ranker.py --train")
        return 1
    
    # Generate test data
    print(f"Generating test data with {args.variations} variations...")
    generator = TrainingDataGenerator(seed=args.seed + 1)  # Different seed
    test_data = generator.generate_all_training_data(
        variations_per_profile=args.variations
    )
    
    # Evaluate
    print(f"Evaluating on {len(test_data)} examples...")
    metrics = ranker.evaluate(test_data, k=args.k)
    
    print_section("Evaluation Results")
    print(f"NDCG@{args.k}: {metrics.get(f'ndcg@{args.k}', 'N/A'):.4f}")
    print(f"Number of queries: {metrics.get('num_queries', 'N/A')}")
    
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    """Test ranking with sample preferences.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print_header("TESTING COURSE RANKING")
    
    config = get_ranking_config()
    if args.model_path:
        config.model_path = args.model_path
    
    # Initialize ranker
    ranker = CourseRanker(model_path=config.model_path, config=config)
    
    if not ranker.is_trained:
        print("WARNING: Model not found or not trained. Using fallback ranking.")
    
    # Parse student preferences
    if args.student_prefs:
        try:
            prefs = json.loads(args.student_prefs)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in student-prefs: {e}")
            return 1
    else:
        # Default preferences
        prefs = {
            "math_interest": 0.9,
            "humanities_interest": 0.2,
            "career_goal": "aerospace_engineer",
        }
    
    print_section("Student Preferences")
    for key, value in prefs.items():
        print(f"  {key}: {value}")
    
    # Create sample recommendations
    print_section("Creating Sample Recommendations")
    recommendations = []
    
    for course_id, course_info in COURSE_CATALOG.items():
        # Calculate features based on preferences
        math_match = 1.0 - abs(prefs.get("math_interest", 0.5) - course_info["math_intensity"])
        humanities_match = 1.0 - abs(prefs.get("humanities_interest", 0.5) - course_info["humanities_intensity"])
        career_score = 1.0 if prefs.get("career_goal", "") in course_info["careers"] else 0.0
        
        rec = CourseRecommendation(
            course_id=course_id,
            course_name=course_info["name"],
            department=course_info["careers"][0][:3].upper() if course_info["careers"] else "GEN",
            description=f"Course in {course_info['name']}",
            career_paths=course_info["careers"],
            credits=course_info["credits"],
            math_intensity=course_info["math_intensity"],
            humanities_intensity=course_info["humanities_intensity"],
            total_score=math_match * 0.4 + career_score * 0.4 + humanities_match * 0.2,
            vector_similarity_score=math_match * 0.6 + humanities_match * 0.4,
            career_match_score=career_score,
            math_intensity_match=math_match,
            humanities_intensity_match=humanities_match,
            graph_distance=1.0,
            prerequisite_score=1.0,
            features={
                "vector_similarity_score": math_match * 0.6 + humanities_match * 0.4,
                "career_match_score": career_score,
                "math_intensity_match": math_match,
                "humanities_intensity_match": humanities_match,
                "graph_distance": 1.0,
                "prerequisite_score": 1.0,
                "course_credits": float(course_info["credits"]),
                "student_math_interest": prefs.get("math_interest", 0.5),
                "student_humanities_interest": prefs.get("humanities_interest", 0.5),
            },
        )
        recommendations.append(rec)
    
    # Sort by initial score
    recommendations.sort(key=lambda r: r.total_score, reverse=True)
    
    print("Before XGBoost ranking:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec.course_name:30s} (score: {rec.total_score:.3f})")
    
    # Apply XGBoost ranking
    if ranker.is_trained:
        reranked = ranker.rank(recommendations)
        
        print_section("After XGBoost ranking:")
        for i, rec in enumerate(reranked, 1):
            xgboost_score = rec.features.get("xgboost_score", rec.total_score)
            original = rec.features.get("original_total_score", rec.total_score)
            print(f"  {i}. {rec.course_name:30s} (xgboost: {xgboost_score:.3f}, original: {original:.3f})")
        
        # Show position changes
        print_section("Position Changes")
        before_pos = {r.course_id: i for i, r in enumerate(recommendations, 1)}
        after_pos = {r.course_id: i for i, r in enumerate(reranked, 1)}
        
        for course_id in before_pos:
            change = before_pos[course_id] - after_pos[course_id]
            arrow = "↑" if change > 0 else ("↓" if change < 0 else "→")
            print(f"  {course_id}: {before_pos[course_id]} {arrow} {after_pos[course_id]}")
    else:
        print("\n(No XGBoost model - using heuristic ranking)")
    
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show model information.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    print_header("XGBOOST RANKER INFORMATION")
    
    config = get_ranking_config()
    if args.model_path:
        config.model_path = args.model_path
    
    print_section("Configuration")
    print(f"Model path: {config.model_path}")
    print(f"Training data path: {config.training_data_path}")
    print(f"Objective: {config.objective}")
    print(f"N_estimators: {config.n_estimators}")
    print(f"Max_depth: {config.max_depth}")
    print(f"Learning_rate: {config.learning_rate}")
    print(f"Random_state: {config.random_state}")
    
    print_section("Feature Names")
    for i, name in enumerate(config.feature_names, 1):
        print(f"  {i}. {name}")
    
    # Initialize ranker
    ranker = CourseRanker(model_path=config.model_path, config=config)
    
    print_section("Model Status")
    if ranker.is_trained:
        print("Status: TRAINED ✓")
        
        # Feature importance
        importance = ranker.get_feature_importance()
        if importance:
            print_section("Feature Importance")
            for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(score * 50)
                print(f"  {feature:35s} {score:.3f} {bar}")
    else:
        print("Status: NOT TRAINED ✗")
        print(f"Run: python scripts/train_ranker.py --train")
    
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="XGBoost Ranker Training CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate training data
  python scripts/train_ranker.py --generate-data --variations 30
  
  # Train the model
  python scripts/train_ranker.py --train --variations 30
  
  # Evaluate on test data
  python scripts/train_ranker.py --evaluate --variations 10
  
  # Test ranking
  python scripts/train_ranker.py --rank
  
  # Show model info
  python scripts/train_ranker.py --info
  
  # Full pipeline
  python scripts/train_ranker.py --generate-data --train --evaluate
        """
    )
    
    # Commands
    parser.add_argument(
        "--generate-data",
        action="store_true",
        help="Generate synthetic training data",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train the XGBoost model",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Evaluate model performance",
    )
    parser.add_argument(
        "--rank",
        action="store_true",
        help="Test ranking with sample preferences",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show model information",
    )
    
    # Options
    parser.add_argument(
        "--variations",
        type=int,
        default=20,
        help="Number of variations per profile (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        help="Path to model file",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Rank cutoff for NDCG evaluation (default: 5)",
    )
    parser.add_argument(
        "--student-prefs",
        type=str,
        help='Student preferences as JSON (e.g., \'{"math_interest": 0.9}\')',
    )
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if not any([args.generate_data, args.train, args.evaluate, args.rank, args.info]):
        parser.print_help()
        return 0
    
    # Execute commands
    exit_code = 0
    
    if args.generate_data:
        exit_code = cmd_generate_data(args) or exit_code
    
    if args.train:
        exit_code = cmd_train(args) or exit_code
    
    if args.evaluate:
        exit_code = cmd_evaluate(args) or exit_code
    
    if args.rank:
        exit_code = cmd_rank(args) or exit_code
    
    if args.info:
        exit_code = cmd_info(args) or exit_code
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
