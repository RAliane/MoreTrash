from typing import Dict, List, Any, Optional
import numpy as np
import structlog
import pickle
import os

from app.infrastructure.config import settings
from app.infrastructure.logging import get_ml_logger

logger = get_ml_logger()


class XGBoostEngine:
    """XGBoost-based ML scoring engine."""

    def __init__(self):
        self.model_path = settings.XGBOOST_MODEL_PATH
        self.parameters = settings.XGBOOST_PARAMETERS
        self.model = None
        self.is_loaded = False

    async def load_model(self) -> bool:
        """Load XGBoost model from disk."""
        try:
            model_file = os.path.join(self.model_path, "xgboost_model.pkl")

            if os.path.exists(model_file):
                with open(model_file, "rb") as f:
                    self.model = pickle.load(f)
                self.is_loaded = True
                logger.info("XGBoost model loaded successfully")
                return True
            else:
                logger.warning("XGBoost model file not found, using default scoring")
                return False

        except Exception as e:
            logger.error("Failed to load XGBoost model", error=str(e))
            return False

    async def score_solution(self, features: np.ndarray) -> float:
        """Score a solution using XGBoost model."""
        try:
            if not self.is_loaded:
                # Fallback scoring without model
                return self._fallback_scoring(features)

            if self.model is None:
                await self.load_model()

            if self.model is None:
                return self._fallback_scoring(features)

            # Make prediction
            prediction = self.model.predict(features)[0]

            logger.debug(
                "XGBoost prediction generated",
                prediction=float(prediction),
                feature_count=features.shape[1],
            )

            return float(prediction)

        except Exception as e:
            logger.warning("XGBoost scoring failed, using fallback", error=str(e))
            return self._fallback_scoring(features)

    def _fallback_scoring(self, features: np.ndarray) -> float:
        """Fallback scoring when model is not available."""
        # Simple scoring based on feature values
        score = 0.0

        for i, feature in enumerate(features.flatten()):
            # Weighted sum with some randomness
            weight = 1.0 / (i + 1)  # Decreasing weights
            score += feature * weight

        # Normalize to [0, 1] range
        score = max(0.0, min(1.0, score))

        logger.debug("Fallback scoring used", score=score)
        return score

    async def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the model."""
        try:
            if not self.is_loaded or self.model is None:
                return {}

            importance = self.model.get_booster().get_score(importance_type="gain")

            # Convert to relative importance
            total = sum(importance.values())
            if total > 0:
                relative_importance = {k: v / total for k, v in importance.items()}
            else:
                relative_importance = importance

            logger.debug(
                "Feature importance calculated",
                top_features=list(relative_importance.keys())[:5],
            )

            return relative_importance

        except Exception as e:
            logger.warning("Failed to get feature importance", error=str(e))
            return {}

    async def train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> bool:
        """Train a new XGBoost model."""
        try:
            # Lazy import to avoid dependency issues
            import xgboost as xgb

            # Create DMatrix
            dtrain = xgb.DMatrix(X_train, label=y_train)

            if feature_names:
                dtrain.feature_names = feature_names

            # Train model
            self.model = xgb.train(
                self.parameters, dtrain, num_boost_round=100, verbose_eval=False
            )

            # Save model
            os.makedirs(self.model_path, exist_ok=True)
            model_file = os.path.join(self.model_path, "xgboost_model.pkl")

            with open(model_file, "wb") as f:
                pickle.dump(self.model, f)

            self.is_loaded = True

            logger.info(
                "XGBoost model trained and saved",
                samples=X_train.shape[0],
                features=X_train.shape[1],
            )

            return True

        except Exception as e:
            logger.error("XGBoost model training failed", error=str(e))
            return False
