"""Synthetic training data generator for XGBoost ranking.

Generates preference pairs for learning-to-rank training.
"""

import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

from src.ranking.config import get_ranking_config


@dataclass
class TrainingExample:
    """A single training example for learning-to-rank.
    
    Attributes:
        query_id: Unique identifier for the query (student preference profile)
        features: Feature vector for the course
        relevance_score: Relevance label (higher = more relevant)
        course_id: Course identifier
        course_name: Human-readable course name
        student_prefs: Student preference snapshot
    """
    query_id: str
    features: Dict[str, float]
    relevance_score: int
    course_id: str
    course_name: str
    student_prefs: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query_id": self.query_id,
            "features": self.features,
            "relevance_score": self.relevance_score,
            "course_id": self.course_id,
            "course_name": self.course_name,
            "student_prefs": self.student_prefs,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingExample":
        """Create from dictionary."""
        return cls(
            query_id=data["query_id"],
            features=data["features"],
            relevance_score=data["relevance_score"],
            course_id=data["course_id"],
            course_name=data["course_name"],
            student_prefs=data["student_prefs"],
        )


# Course catalog with intensity profiles
COURSE_CATALOG = {
    "aerospace_eng": {
        "name": "Aerospace Engineering",
        "math_intensity": 0.95,
        "humanities_intensity": 0.1,
        "credits": 4,
        "careers": ["aerospace_engineer", "mechanical_engineer"],
    },
    "mechanical_eng": {
        "name": "Mechanical Engineering",
        "math_intensity": 0.85,
        "humanities_intensity": 0.15,
        "credits": 4,
        "careers": ["mechanical_engineer", "aerospace_engineer"],
    },
    "computer_science": {
        "name": "Computer Science",
        "math_intensity": 0.80,
        "humanities_intensity": 0.2,
        "credits": 4,
        "careers": ["software_engineer", "data_scientist"],
    },
    "data_science": {
        "name": "Data Science",
        "math_intensity": 0.75,
        "humanities_intensity": 0.25,
        "credits": 4,
        "careers": ["data_scientist", "software_engineer"],
    },
    "philosophy": {
        "name": "Philosophy",
        "math_intensity": 0.2,
        "humanities_intensity": 0.95,
        "credits": 3,
        "careers": ["philosopher", "writer", "teacher"],
    },
}

# Student preference profiles
STUDENT_PROFILES = {
    "aerospace_engineer": {
        "math_interest": 0.9,
        "humanities_interest": 0.2,
        "career_goal": "aerospace_engineer",
        "ideal_ranking": ["aerospace_eng", "mechanical_eng", "data_science", "computer_science", "philosophy"],
    },
    "software_engineer": {
        "math_interest": 0.8,
        "humanities_interest": 0.3,
        "career_goal": "software_engineer",
        "ideal_ranking": ["computer_science", "data_science", "mechanical_eng", "aerospace_eng", "philosophy"],
    },
    "data_scientist": {
        "math_interest": 0.85,
        "humanities_interest": 0.4,
        "career_goal": "data_scientist",
        "ideal_ranking": ["data_science", "computer_science", "aerospace_eng", "mechanical_eng", "philosophy"],
    },
    "mechanical_engineer": {
        "math_interest": 0.85,
        "humanities_interest": 0.2,
        "career_goal": "mechanical_engineer",
        "ideal_ranking": ["mechanical_eng", "aerospace_eng", "computer_science", "data_science", "philosophy"],
    },
    "humanities_scholar": {
        "math_interest": 0.2,
        "humanities_interest": 0.95,
        "career_goal": "philosopher",
        "ideal_ranking": ["philosophy", "data_science", "computer_science", "mechanical_eng", "aerospace_eng"],
    },
    "balanced_student": {
        "math_interest": 0.6,
        "humanities_interest": 0.6,
        "career_goal": "",
        "ideal_ranking": ["computer_science", "data_science", "mechanical_eng", "philosophy", "aerospace_eng"],
    },
}


class TrainingDataGenerator:
    """Generate synthetic training data for XGBoost learning-to-rank."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.config = get_ranking_config()
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        
    def generate_training_example(
        self,
        profile_name: str,
        course_id: str,
        position: int,
        query_id: str,
        add_noise: bool = True,
    ) -> TrainingExample:
        """Generate a single training example.
        
        Args:
            profile_name: Student profile name
            course_id: Course identifier
            position: Position in ideal ranking (0 = best)
            query_id: Query identifier
            add_noise: Add random noise to features
            
        Returns:
            TrainingExample instance
        """
        profile = STUDENT_PROFILES[profile_name]
        course = COURSE_CATALOG[course_id]
        
        # Calculate features based on alignment
        math_match = 1.0 - abs(profile["math_interest"] - course["math_intensity"])
        humanities_match = 1.0 - abs(profile["humanities_interest"] - course["humanities_intensity"])
        
        # Career match
        career_score = 1.0 if profile["career_goal"] in course["careers"] else 0.0
        
        # Vector similarity (simulated based on alignment)
        vector_sim = (math_match * 0.6 + humanities_match * 0.4) * 0.8 + 0.2
        
        # Graph distance (simulated)
        graph_dist = self.rng.uniform(0.5, 3.0)
        
        # Prerequisite score
        prereq_score = self.rng.uniform(0.7, 1.0)
        
        # Add noise
        if add_noise:
            noise_factor = 0.05
            vector_sim = np.clip(vector_sim + self.np_rng.normal(0, noise_factor), 0, 1)
            career_score = np.clip(career_score + self.np_rng.normal(0, noise_factor), 0, 1)
            math_match = np.clip(math_match + self.np_rng.normal(0, noise_factor), 0, 1)
            humanities_match = np.clip(humanities_match + self.np_rng.normal(0, noise_factor), 0, 1)
            graph_dist = np.clip(graph_dist + self.np_rng.normal(0, noise_factor * 2), 0.1, 5)
            prereq_score = np.clip(prereq_score + self.np_rng.normal(0, noise_factor), 0, 1)
        
        # Build feature dictionary (must match config.feature_names order)
        features = {
            "vector_similarity_score": float(vector_sim),
            "career_match_score": float(career_score),
            "math_intensity_match": float(math_match),
            "humanities_intensity_match": float(humanities_match),
            "graph_distance": float(graph_dist),
            "prerequisite_score": float(prereq_score),
            "course_credits": float(course["credits"]),
            "student_math_interest": float(profile["math_interest"]),
            "student_humanities_interest": float(profile["humanities_interest"]),
        }
        
        # Relevance score: higher rank = higher score (5 levels)
        # Position 0 = relevance 5, Position 4 = relevance 1
        relevance_score = max(1, 5 - position)
        
        return TrainingExample(
            query_id=query_id,
            features=features,
            relevance_score=relevance_score,
            course_id=course_id,
            course_name=course["name"],
            student_prefs={
                "profile": profile_name,
                "math_interest": profile["math_interest"],
                "humanities_interest": profile["humanities_interest"],
                "career_goal": profile["career_goal"],
            },
        )
    
    def generate_profile_examples(
        self,
        profile_name: str,
        num_variations: int = 10,
    ) -> List[TrainingExample]:
        """Generate training examples for a student profile.
        
        Args:
            profile_name: Student profile name
            num_variations: Number of query variations to generate
            
        Returns:
            List of training examples
        """
        profile = STUDENT_PROFILES[profile_name]
        examples = []
        
        for var_idx in range(num_variations):
            query_id = f"{profile_name}_q{var_idx}"
            
            for pos, course_id in enumerate(profile["ideal_ranking"]):
                example = self.generate_training_example(
                    profile_name=profile_name,
                    course_id=course_id,
                    position=pos,
                    query_id=query_id,
                    add_noise=True,
                )
                examples.append(example)
        
        return examples
    
    def generate_all_training_data(
        self,
        variations_per_profile: int = 20,
    ) -> List[TrainingExample]:
        """Generate complete training dataset.
        
        Args:
            variations_per_profile: Number of query variations per profile
            
        Returns:
            List of all training examples
        """
        all_examples = []
        
        for profile_name in STUDENT_PROFILES.keys():
            examples = self.generate_profile_examples(
                profile_name=profile_name,
                num_variations=variations_per_profile,
            )
            all_examples.extend(examples)
        
        return all_examples
    
    def save_training_data(
        self,
        examples: List[TrainingExample],
        output_path: str = None,
    ) -> str:
        """Save training data to JSONL file.
        
        Args:
            examples: List of training examples
            output_path: Output file path (default: from config)
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = self.config.training_data_path
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            for example in examples:
                f.write(json.dumps(example.to_dict()) + "\n")
        
        return str(path)
    
    def load_training_data(self, input_path: str = None) -> List[TrainingExample]:
        """Load training data from JSONL file.
        
        Args:
            input_path: Input file path (default: from config)
            
        Returns:
            List of training examples
        """
        if input_path is None:
            input_path = self.config.training_data_path
        
        examples = []
        with open(input_path, "r") as f:
            for line in f:
                data = json.loads(line.strip())
                examples.append(TrainingExample.from_dict(data))
        
        return examples
    
    def get_statistics(self, examples: List[TrainingExample]) -> Dict[str, Any]:
        """Get statistics about training data.
        
        Args:
            examples: List of training examples
            
        Returns:
            Dictionary of statistics
        """
        if not examples:
            return {}
        
        # Count by query
        query_counts = {}
        relevance_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        course_counts = {}
        profile_counts = {}
        
        for ex in examples:
            query_counts[ex.query_id] = query_counts.get(ex.query_id, 0) + 1
            relevance_dist[ex.relevance_score] = relevance_dist.get(ex.relevance_score, 0) + 1
            course_counts[ex.course_id] = course_counts.get(ex.course_id, 0) + 1
            
            profile = ex.student_prefs.get("profile", "unknown")
            profile_counts[profile] = profile_counts.get(profile, 0) + 1
        
        # Feature statistics
        feature_sums = {name: 0.0 for name in self.config.feature_names}
        for ex in examples:
            for name, value in ex.features.items():
                if name in feature_sums:
                    feature_sums[name] += value
        
        feature_means = {
            name: total / len(examples) 
            for name, total in feature_sums.items()
        }
        
        return {
            "total_examples": len(examples),
            "unique_queries": len(query_counts),
            "unique_courses": len(course_counts),
            "relevance_distribution": relevance_dist,
            "examples_per_query": len(examples) / len(query_counts) if query_counts else 0,
            "course_distribution": course_counts,
            "profile_distribution": profile_counts,
            "feature_means": feature_means,
        }


def generate_training_data(variations_per_profile: int = 20, seed: int = 42) -> str:
    """Convenience function to generate and save training data.
    
    Args:
        variations_per_profile: Number of variations per profile
        seed: Random seed
        
    Returns:
        Path to saved training data file
    """
    generator = TrainingDataGenerator(seed=seed)
    examples = generator.generate_all_training_data(
        variations_per_profile=variations_per_profile
    )
    
    output_path = generator.save_training_data(examples)
    stats = generator.get_statistics(examples)
    
    print(f"Training data saved to: {output_path}")
    print(f"Total examples: {stats['total_examples']}")
    print(f"Unique queries: {stats['unique_queries']}")
    print(f"Relevance distribution: {stats['relevance_distribution']}")
    
    return output_path


if __name__ == "__main__":
    # Generate training data when run directly
    generate_training_data(variations_per_profile=20)
