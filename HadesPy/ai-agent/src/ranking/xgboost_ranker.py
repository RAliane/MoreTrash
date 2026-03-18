"""XGBoost learning-to-rank for course recommendation optimization.

Integrates with the existing XGBoost engine from Branch/fastapi_xgboost_optimizer
and provides learning-to-rank capabilities for reranking course recommendations.

Deterministic ranking is enforced through:
- Fixed random_state (42) for all RNG operations
- Sorted feature extraction
- Deterministic tie-breaking (score DESC, entity_id ASC)
"""

import json
import os
import random
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.logging_config import get_logger
from src.ranking.config import (
    get_ranking_config,
    RankingConfig,
    RANKER_RANDOM_STATE,
    RANKER_FEATURE_SCHEMA,
)
from src.ranking.training_data import TrainingExample, TrainingDataGenerator
from src.rag.course_recommender import CourseRecommendation

logger = get_logger(__name__)

# Try to import xgboost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    logger.warning("XGBoost not available. Running in fallback mode.")
    XGBOOST_AVAILABLE = False
    xgb = None


class CourseRanker:
    """XGBoost-based course recommendation ranker.
    
    Uses learning-to-rank (pairwise) to rerank course recommendations
    based on learned preferences from training data.
    
    Attributes:
        config: RankingConfig instance
        model: XGBoost ranker model
        is_trained: Whether model has been trained
        feature_names: Ordered list of feature names
    
    Example:
        >>> ranker = CourseRanker()
        >>> ranker.train(training_data)
        >>> reranked = ranker.rank(recommendations)
    """
    
    def __init__(self, model_path: Optional[str] = None, config: Optional[RankingConfig] = None):
        """Initialize the CourseRanker.
        
        Args:
            model_path: Path to load/save model (default: from config)
            config: RankingConfig instance (default: from environment)
        """
        self.config = config or get_ranking_config()
        self.model_path = model_path or self.config.model_path
        self.model = None
        self.is_trained = False
        self.feature_names = self.config.feature_names
        
        # Ensure model directory exists
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "CourseRanker initialized",
            model_path=self.model_path,
            objective=self.config.objective,
            n_estimators=self.config.n_estimators,
        )
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load model from disk if available.
        
        Returns:
            True if model loaded successfully
        """
        if not XGBOOST_AVAILABLE:
            logger.warning("XGBoost not available, cannot load model")
            return False
        
        model_file = Path(self.model_path)
        if not model_file.exists():
            logger.info("No existing model found, will train new model")
            return False
        
        try:
            self.model = xgb.XGBRanker()
            self.model.load_model(str(model_file))
            self.is_trained = True
            logger.info("Loaded existing XGBoost model", path=str(model_file))
            return True
        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            return False
    
    def load_model(self) -> bool:
        """Public method to load model from disk.
        
        Returns:
            True if model loaded successfully
        """
        return self._load_model()
    
    def _save_model(self) -> bool:
        """Save model to disk.
        
        Returns:
            True if model saved successfully
        """
        if not self.model or not self.is_trained:
            logger.warning("No trained model to save")
            return False
        
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(self.model_path)
            logger.info("Saved XGBoost model", path=self.model_path)
            
            # Save feature names metadata
            metadata_path = str(Path(self.model_path).with_suffix(".metadata.json"))
            metadata = {
                "feature_names": self.feature_names,
                "config": {
                    "objective": self.config.objective,
                    "n_estimators": self.config.n_estimators,
                    "max_depth": self.config.max_depth,
                    "learning_rate": self.config.learning_rate,
                },
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            return True
        except Exception as e:
            logger.error("Failed to save model", error=str(e))
            return False
    
    def _extract_features(self, rec: CourseRecommendation) -> np.ndarray:
        """Extract feature vector from a CourseRecommendation.
        
        Features are extracted in sorted order for determinism.
        Uses OrderedDict internally to maintain consistent ordering.
        
        Args:
            rec: CourseRecommendation to extract features from
            
        Returns:
            NumPy array of features in deterministic order
        """
        # Use OrderedDict with sorted keys for determinism
        feature_dict = OrderedDict()
        
        # First, collect all available features from rec.features dict
        for name in sorted(rec.features.keys()):
            feature_dict[name] = float(rec.features[name])
        
        # Add any missing features from direct attributes
        for name in sorted(self.feature_names):
            if name not in feature_dict:
                if hasattr(rec, name):
                    feature_dict[name] = float(getattr(rec, name))
                else:
                    logger.warning(f"Feature '{name}' not found, using 0.0")
                    feature_dict[name] = 0.0
        
        # Return features in sorted order
        features = [feature_dict[name] for name in sorted(feature_dict.keys())]
        
        return np.array(features).reshape(1, -1)
    
    def _prepare_training_data(
        self,
        training_data: List[TrainingExample],
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Prepare training data for XGBoost.
        
        Features are extracted deterministically by sorting feature names
        to ensure identical feature ordering across runs.
        
        Args:
            training_data: List of TrainingExample objects
            
        Returns:
            Tuple of (X, y, groups) where groups identifies query IDs
        """
        # Build feature matrix
        X_list = []
        y_list = []
        groups = []
        
        # Group by query_id (sorted for determinism)
        query_map = {}
        sorted_training_data = sorted(training_data, key=lambda x: x.query_id)
        
        for example in sorted_training_data:
            if example.query_id not in query_map:
                query_map[example.query_id] = len(query_map)
            
            # Extract features in sorted order for determinism
            sorted_features = sorted(example.features.keys())
            features = [example.features.get(name, 0.0) for name in sorted_features]
            X_list.append(features)
            y_list.append(example.relevance_score)
            groups.append(query_map[example.query_id])
        
        X = pd.DataFrame(X_list, columns=sorted_features)
        y = pd.Series(y_list, name="relevance")
        groups = pd.Series(groups, name="group")
        
        return X, y, groups
    
    def train(
        self,
        training_data: List[TrainingExample],
        validation_fraction: float = 0.1,
    ) -> Dict[str, Any]:
        """Train the XGBoost ranking model.
        
        Uses XGBoost's learning-to-rank (pairwise) objective.
        
        Deterministic training is enforced through:
        - Fixed random_state for XGBRanker
        - Seeded NumPy and Python RNGs
        - Sorted feature extraction
        
        Args:
            training_data: List of TrainingExample objects
            validation_fraction: Fraction of data for validation
            
        Returns:
            Dictionary with training metrics
        """
        if not XGBOOST_AVAILABLE:
            raise RuntimeError("XGBoost is not available. Install with: pip install xgboost")
        
        if len(training_data) < self.config.min_training_samples:
            logger.warning(
                "Insufficient training data",
                num_samples=len(training_data),
                min_required=self.config.min_training_samples,
            )
            return {"status": "failed", "reason": "insufficient_data"}
        
        # Set deterministic random seeds
        np.random.seed(RANKER_RANDOM_STATE)
        random.seed(RANKER_RANDOM_STATE)
        
        logger.info(
            "Starting model training",
            num_samples=len(training_data),
            num_features=len(self.feature_names),
            random_state=RANKER_RANDOM_STATE,
        )
        
        # Prepare training data (features are sorted deterministically)
        X, y, groups = self._prepare_training_data(training_data)
        
        # Split into train/validation
        unique_groups = groups.unique()
        n_val = max(1, int(len(unique_groups) * validation_fraction))
        
        # Random split by group to avoid data leakage (seed already set above)
        val_groups = np.random.choice(unique_groups, size=n_val, replace=False)
        
        train_mask = ~groups.isin(val_groups)
        val_mask = groups.isin(val_groups)
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_val, y_val = X[val_mask], y[val_mask]
        groups_train = groups[train_mask]
        groups_val = groups[val_mask]
        
        # Group sizes for XGBoost
        train_group_sizes = groups_train.value_counts().sort_index().values
        val_group_sizes = groups_val.value_counts().sort_index().values
        
        # Create and train model
        self.model = xgb.XGBRanker(**self.config.xgboost_params)
        
        try:
            self.model.fit(
                X_train, y_train,
                group=train_group_sizes,
                eval_set=[(X_val, y_val)],
                eval_group=[val_group_sizes],
                verbose=False,
            )
            
            self.is_trained = True
            
            # Save model
            self._save_model()
            
            # Calculate training metrics
            train_predictions = self.model.predict(X_train)
            val_predictions = self.model.predict(X_val)
            
            metrics = {
                "status": "success",
                "num_training_samples": len(X_train),
                "num_validation_samples": len(X_val),
                "num_features": len(self.feature_names),
                "training_score_mean": float(np.mean(train_predictions)),
                "validation_score_mean": float(np.mean(val_predictions)),
                "feature_importance": self.get_feature_importance(),
            }
            
            logger.info("Model training completed", **metrics)
            return metrics
            
        except Exception as e:
            logger.error("Model training failed", error=str(e))
            return {"status": "failed", "error": str(e)}
    
    def rank(
        self,
        recommendations: List[CourseRecommendation],
        rerank_top_k: Optional[int] = None,
    ) -> List[CourseRecommendation]:
        """Rerank course recommendations using XGBoost.
        
        Deterministic reranking with tie-breaking:
        - Primary: score DESC (higher scores first)
        - Secondary: course_id ASC (alphabetical for ties)
        
        Args:
            recommendations: List of CourseRecommendation objects
            rerank_top_k: Only rerank top k items (for efficiency)
            
        Returns:
            Reranked list of CourseRecommendation objects
        """
        if not recommendations:
            return []
        
        # If model not trained, return with deterministic tie-breaking
        if not self.is_trained or not XGBOOST_AVAILABLE:
            logger.debug("Model not trained, returning deterministic ranking")
            return sorted(
                recommendations,
                key=lambda r: (-r.total_score, r.course_id),
            )
        
        # Limit to top_k if specified
        if rerank_top_k and len(recommendations) > rerank_top_k:
            to_rerank = recommendations[:rerank_top_k]
            remainder = recommendations[rerank_top_k:]
        else:
            to_rerank = recommendations
            remainder = []
        
        # Extract features and predict scores (input order preserved)
        predictions = []
        for rec in to_rerank:
            features = self._extract_features(rec)
            score = float(self.model.predict(features)[0])
            predictions.append((rec, score))
        
        # Sort by XGBoost score DESC, then course_id ASC for deterministic tie-breaking
        predictions.sort(key=lambda x: (-x[1], x[0].course_id))
        
        # Update recommendations with new scores
        reranked = []
        for rec, xgboost_score in predictions:
            # Store original score and add XGBoost score
            rec.features["xgboost_score"] = xgboost_score
            rec.features["original_score"] = rec.total_score
            
            # Update total score to use XGBoost prediction
            rec.total_score = xgboost_score
            reranked.append(rec)
        
        # Add remainder if any (maintain input order)
        if remainder:
            reranked.extend(remainder)
        
        logger.debug(
            "Reranking complete",
            input_count=len(recommendations),
            output_count=len(reranked),
        )
        
        return reranked
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained or not self.model:
            return {}
        
        importance = self.model.get_booster().get_score(importance_type="gain")
        
        # Map to feature names
        named_importance = {}
        for key, value in importance.items():
            # XGBoost returns features as 'f0', 'f1', etc.
            if key.startswith("f"):
                idx = int(key[1:])
                if idx < len(self.feature_names):
                    named_importance[self.feature_names[idx]] = float(value)
            else:
                named_importance[key] = float(value)
        
        # Normalize to sum to 1
        total = sum(named_importance.values())
        if total > 0:
            named_importance = {k: v / total for k, v in named_importance.items()}
        
        return named_importance
    
    def get_feature_schema(self) -> List[str]:
        """Return the fixed feature schema for deterministic ranking.
        
        Returns a sorted list of feature names to ensure consistent
        feature ordering across training and inference.
        
        Returns:
            Sorted list of feature names per TOML specification:
            - graph_centrality
            - vector_similarity
            - course_difficulty
            - career_alignment_score
            - prerequisite_depth
        """
        return sorted(RANKER_FEATURE_SCHEMA)
    
    def evaluate(
        self,
        test_data: List[TrainingExample],
        k: int = 5,
    ) -> Dict[str, float]:
        """Evaluate model performance on test data.
        
        Calculates NDCG@k and other ranking metrics.
        
        Args:
            test_data: List of test examples
            k: Rank cutoff for metrics
            
        Returns:
            Dictionary of evaluation metrics
        """
        if not self.is_trained:
            return {"error": "Model not trained"}
        
        # Group by query
        queries = {}
        for example in test_data:
            if example.query_id not in queries:
                queries[example.query_id] = []
            queries[example.query_id].append(example)
        
        ndcg_scores = []
        
        for query_id, examples in queries.items():
            # Extract features and predict
            X = pd.DataFrame(
                [[ex.features.get(name, 0.0) for name in self.feature_names] for ex in examples],
                columns=self.feature_names,
            )
            predictions = self.model.predict(X)
            
            # Get relevance scores
            relevances = [ex.relevance_score for ex in examples]
            
            # Calculate NDCG
            ndcg = self._calculate_ndcg(relevances, predictions, k)
            ndcg_scores.append(ndcg)
        
        return {
            f"ndcg@{k}": float(np.mean(ndcg_scores)),
            "num_queries": len(queries),
        }
    
    def _calculate_ndcg(
        self,
        relevances: List[int],
        predictions: np.ndarray,
        k: int,
    ) -> float:
        """Calculate NDCG@k metric.
        
        Args:
            relevances: Ground truth relevance scores
            predictions: Model predictions
            k: Rank cutoff
            
        Returns:
            NDCG@k score
        """
        # Sort by predictions (descending)
        order = np.argsort(predictions)[::-1][:k]
        
        # Calculate DCG
        dcg = 0.0
        for i, idx in enumerate(order, 1):
            rel = relevances[idx]
            dcg += (2 ** rel - 1) / np.log2(i + 1)
        
        # Calculate ideal DCG
        ideal_order = np.argsort(relevances)[::-1][:k]
        idcg = 0.0
        for i, idx in enumerate(ideal_order, 1):
            rel = relevances[idx]
            idcg += (2 ** rel - 1) / np.log2(i + 1)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def train_from_generator(
        self,
        variations_per_profile: int = 20,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Convenience method to generate and train on synthetic data.
        
        Args:
            variations_per_profile: Number of variations per student profile
            seed: Random seed
            
        Returns:
            Training metrics
        """
        generator = TrainingDataGenerator(seed=seed)
        training_data = generator.generate_all_training_data(
            variations_per_profile=variations_per_profile
        )
        
        # Save training data for reference
        generator.save_training_data(training_data)
        
        stats = generator.get_statistics(training_data)
        logger.info("Generated training data", **stats)
        
        return self.train(training_data)


# Singleton instance for convenience
_ranker_instance: Optional[CourseRanker] = None


def get_ranker(model_path: Optional[str] = None) -> CourseRanker:
    """Get or create singleton CourseRanker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        _ranker_instance = CourseRanker(model_path=model_path)
    return _ranker_instance
