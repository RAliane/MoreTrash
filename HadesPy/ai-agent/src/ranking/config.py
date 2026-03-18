"""XGBoost ranking configuration.

Hyperparameters and settings for the learning-to-rank model.

Determinism is enforced through:
- Fixed RANKER_RANDOM_STATE (42) for all RNG operations
- RANKER_DETERMINISM_CHECK flag for validation
- Stable RANKER_FEATURE_SCHEMA for consistent features
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import os


# Determinism constants per TOML specification
RANKER_RANDOM_STATE: int = 42
"""Fixed random seed for reproducible ranking across runs."""

RANKER_DETERMINISM_CHECK: bool = True
"""Flag to enable determinism validation in ranking operations."""

RANKER_FEATURE_SCHEMA: List[str] = [
    "graph_centrality",
    "vector_similarity",
    "course_difficulty",
    "career_alignment_score",
    "prerequisite_depth",
]
"""Fixed feature schema for deterministic ranking.

Per TOML specification, these features are used in consistent order:
- graph_centrality: Graph-based centrality measure
- vector_similarity: Semantic similarity score (0-1)
- course_difficulty: Normalized difficulty rating
- career_alignment_score: Career path alignment (0-1)
- prerequisite_depth: Prerequisite chain depth
"""


@dataclass
class RankingConfig:
    """Configuration for XGBoost learning-to-rank.
    
    Attributes:
        model_path: Path to save/load the trained model
        n_estimators: Number of gradient boosted trees
        max_depth: Maximum tree depth
        learning_rate: Learning rate (eta)
        subsample: Subsample ratio of training instances
        colsample_bytree: Subsample ratio of columns
        objective: XGBoost objective function
        eval_metric: Evaluation metric for training
        random_state: Random seed for reproducibility
        early_stopping_rounds: Early stopping rounds
        feature_names: Ordered list of feature names
        feature_importance_weights: Custom feature weights
        training_schedule: Training schedule settings
        use_gpu: Whether to use GPU acceleration
        pairwise_margin: Margin for pairwise ranking
    """
    
    # Model persistence
    model_path: str = "artifacts/models/ranker.json"
    training_data_path: str = "artifacts/training_data.jsonl"
    
    # XGBoost hyperparameters
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    
    # Learning-to-rank specific
    objective: str = "rank:pairwise"
    eval_metric: str = "ndcg"
    pairwise_margin: float = 0.1
    
    # Reproducibility
    random_state: int = 42
    
    # Training settings
    early_stopping_rounds: int = 10
    validation_fraction: float = 0.1
    
    # Feature configuration (must match RAG pipeline output)
    feature_names: List[str] = field(default_factory=lambda: [
        "vector_similarity_score",
        "career_match_score",
        "math_intensity_match",
        "humanities_intensity_match",
        "graph_distance",
        "prerequisite_score",
        "course_credits",
        "student_math_interest",
        "student_humanities_interest",
    ])
    
    # Feature importance weights (for weighted ensemble)
    feature_importance_weights: Dict[str, float] = field(default_factory=lambda: {
        "vector_similarity_score": 0.25,
        "career_match_score": 0.30,
        "math_intensity_match": 0.15,
        "humanities_intensity_match": 0.10,
        "graph_distance": 0.10,
        "prerequisite_score": 0.10,
    })
    
    # Training schedule
    retrain_interval_hours: int = 24
    min_training_samples: int = 100
    max_training_samples: int = 10000
    
    # Runtime flags
    use_gpu: bool = False
    debug_mode: bool = False
    
    def __post_init__(self):
        """Ensure directories exist."""
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.training_data_path).parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def xgboost_params(self) -> Dict[str, Any]:
        """Get XGBoost parameters dictionary."""
        params = {
            "objective": self.objective,
            "eval_metric": self.eval_metric,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "random_state": self.random_state,
            "n_estimators": self.n_estimators,
            "verbosity": 1 if self.debug_mode else 0,
        }
        
        if self.use_gpu:
            params["tree_method"] = "gpu_hist"
            params["predictor"] = "gpu_predictor"
        
        return params
    
    @classmethod
    def from_env(cls) -> "RankingConfig":
        """Create config from environment variables."""
        return cls(
            model_path=os.getenv("XGBOOST_MODEL_PATH", "artifacts/models/ranker.json"),
            n_estimators=int(os.getenv("XGBOOST_N_ESTIMATORS", "100")),
            max_depth=int(os.getenv("XGBOOST_MAX_DEPTH", "6")),
            learning_rate=float(os.getenv("XGBOOST_LEARNING_RATE", "0.1")),
            subsample=float(os.getenv("XGBOOST_SUBSAMPLE", "0.8")),
            colsample_bytree=float(os.getenv("XGBOOST_COLSAMPLE_BYTREE", "0.8")),
            random_state=int(os.getenv("XGBOOST_RANDOM_STATE", "42")),
            use_gpu=os.getenv("XGBOOST_USE_GPU", "false").lower() == "true",
            debug_mode=os.getenv("XGBOOST_DEBUG", "false").lower() == "true",
        )


# Singleton config instance
_ranking_config: Optional[RankingConfig] = None


def get_ranking_config() -> RankingConfig:
    """Get the global ranking configuration."""
    global _ranking_config
    if _ranking_config is None:
        _ranking_config = RankingConfig.from_env()
    return _ranking_config
