"""
XGBoost engine for machine learning-based scoring and optimization.

This module implements the XGBoost integration for predictive scoring,
feature engineering, and model management.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

from app.core.config import get_models_dir, settings
from app.core.exceptions import OptimizationException
from app.infrastructure.logging_config import get_logger


class XGBoostEngine:
    """
    XGBoost engine for ML-based scoring and optimization.
    
    Handles model loading, prediction, feature engineering, and
    model management for optimization tasks.
    """
    
    def __init__(self):
        """Initialize the XGBoost engine."""
        self.logger = get_logger(__name__)
        self.models: Dict[str, xgb.XGBModel] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_extractors: Dict[str, Any] = {}
        self.is_ready = False
        
        self.logger.info("XGBoost engine initialized")
    
    async def load_models(self) -> None:
        """
        Load XGBoost models from disk.
        
        Raises:
            OptimizationException: If model loading fails
        """
        try:
            model_dir = Path(settings.XGBOOST_MODEL_PATH)
            
            if not model_dir.exists():
                self.logger.warning(
                    f"Model directory does not exist: {model_dir}",
                    extra={"model_dir": str(model_dir)}
                )
                # Create default models
                await self._create_default_models()
                return
            
            # Load scoring model
            scoring_model_path = model_dir / "scoring_model.json"
            if scoring_model_path.exists():
                self.models["scoring"] = xgb.XGBRegressor()
                self.models["scoring"].load_model(str(scoring_model_path))
                self.logger.info("Scoring model loaded")
            
            # Load constraint satisfaction model
            constraint_model_path = model_dir / "constraint_model.json"
            if constraint_model_path.exists():
                self.models["constraint"] = xgb.XGBClassifier()
                self.models["constraint"].load_model(str(constraint_model_path))
                self.logger.info("Constraint model loaded")
            
            # Load scalers
            await self._load_scalers(model_dir)
            
            # Load feature extractors
            await self._load_feature_extractors(model_dir)
            
            self.is_ready = len(self.models) > 0
            
            self.logger.info(
                "XGBoost models loaded successfully",
                extra={"num_models": len(self.models)}
            )
            
        except Exception as exc:
            self.logger.error(
                "Failed to load XGBoost models",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise OptimizationException(
                message="Failed to load XGBoost models",
                code="XGBOOST_MODEL_LOAD_FAILED",
                engine_error=str(exc),
            )
    
    async def predict(self, features: Dict[str, Any]) -> Dict[str, float]:
        """
        Make predictions using XGBoost models.
        
        Args:
            features: Input features for prediction
            
        Returns:
            Dict[str, float]: Prediction results
            
        Raises:
            OptimizationException: If prediction fails
        """
        if not self.is_ready:
            raise OptimizationException(
                message="XGBoost engine is not ready",
                code="XGBOOST_NOT_READY",
            )
        
        try:
            start_time = time.time()
            
            # Prepare features
            feature_vector = await self._prepare_feature_vector(features)
            
            # Make predictions
            predictions = {}
            
            # Scoring prediction
            if "scoring" in self.models:
                scoring_features = self._extract_scoring_features(feature_vector)
                scoring_prediction = self.models["scoring"].predict(scoring_features)[0]
                predictions["score"] = float(scoring_prediction)
            
            # Constraint satisfaction prediction
            if "constraint" in self.models:
                constraint_features = self._extract_constraint_features(feature_vector)
                constraint_prediction = self.models["constraint"].predict_proba(constraint_features)[0]
                predictions["constraint_satisfaction"] = float(constraint_prediction[1])
            
            # Calculate overall score
            predictions["overall_score"] = await self._calculate_overall_score(predictions)
            
            # Add confidence intervals
            predictions["confidence_intervals"] = await self._calculate_confidence_intervals(
                feature_vector, predictions
            )
            
            # Add prediction metadata
            predictions["prediction_time"] = time.time() - start_time
            predictions["model_version"] = settings.APP_VERSION
            
            self.logger.debug(
                "XGBoost prediction completed",
                extra={
                    "overall_score": predictions["overall_score"],
                    "prediction_time": predictions["prediction_time"],
                }
            )
            
            return predictions
            
        except Exception as exc:
            self.logger.error(
                "XGBoost prediction failed",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise OptimizationException(
                message="XGBoost prediction failed",
                code="XGBOOST_PREDICTION_FAILED",
                engine_error=str(exc),
            )
    
    async def train_model(
        self,
        training_data: pd.DataFrame,
        target_column: str,
        model_type: str = "regression",
        model_name: str = "custom",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Train a new XGBoost model.
        
        Args:
            training_data: Training dataset
            target_column: Target variable column name
            model_type: Model type (regression/classification)
            model_name: Model name for saving
            parameters: XGBoost parameters
            
        Returns:
            str: Path to saved model
            
        Raises:
            OptimizationException: If training fails
        """
        try:
            start_time = time.time()
            
            # Prepare data
            X = training_data.drop(columns=[target_column])
            y = training_data[target_column]
            
            # Set default parameters
            if parameters is None:
                parameters = {
                    "n_estimators": settings.XGBOOST_N_ESTIMATORS,
                    "max_depth": settings.XGBOOST_MAX_DEPTH,
                    "learning_rate": settings.XGBOOST_LEARNING_RATE,
                    "subsample": settings.XGBOOST_SUBSAMPLE,
                    "colsample_bytree": settings.XGBOOST_COLSAMPLE_BYTREE,
                    "random_state": 42,
                }
            
            # Create model
            if model_type == "regression":
                model = xgb.XGBRegressor(**parameters)
            elif model_type == "classification":
                model = xgb.XGBClassifier(**parameters)
            else:
                raise ValueError(f"Invalid model type: {model_type}")
            
            # Train model
            model.fit(X, y)
            
            # Save model
            model_dir = Path(settings.XGBOOST_MODEL_PATH)
            model_dir.mkdir(parents=True, exist_ok=True)
            
            model_path = model_dir / f"{model_name}_model.json"
            model.save_model(str(model_path))
            
            # Store model
            self.models[model_name] = model
            
            # Save training metadata
            metadata = {
                "training_time": time.time() - start_time,
                "model_type": model_type,
                "parameters": parameters,
                "feature_names": list(X.columns),
                "target_column": target_column,
                "training_samples": len(training_data),
            }
            
            metadata_path = model_dir / f"{model_name}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(
                "XGBoost model trained successfully",
                extra={
                    "model_name": model_name,
                    "model_type": model_type,
                    "training_samples": len(training_data),
                    "training_time": metadata["training_time"],
                }
            )
            
            return str(model_path)
            
        except Exception as exc:
            self.logger.error(
                "XGBoost model training failed",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise OptimizationException(
                message="XGBoost model training failed",
                code="XGBOOST_TRAINING_FAILED",
                engine_error=str(exc),
            )
    
    async def get_feature_importance(self, model_name: str = "scoring") -> Dict[str, float]:
        """
        Get feature importance from a trained model.
        
        Args:
            model_name: Model name
            
        Returns:
            Dict[str, float]: Feature importance scores
        """
        if model_name not in self.models:
            raise OptimizationException(
                message=f"Model '{model_name}' not found",
                code="XGBOOST_MODEL_NOT_FOUND",
            )
        
        model = self.models[model_name]
        importance = model.get_booster().get_score(importance_type="weight")
        
        return dict(importance)
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.models.clear()
        self.scalers.clear()
        self.feature_extractors.clear()
        self.is_ready = False
        
        self.logger.info("XGBoost engine cleaned up")
    
    async def _create_default_models(self) -> None:
        """Create default models if none exist."""
        self.logger.info("Creating default XGBoost models")
        
        # Create simple scoring model
        scoring_model = xgb.XGBRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        
        # Train on dummy data
        dummy_X = np.random.rand(100, 10)
        dummy_y = np.random.rand(100)
        scoring_model.fit(dummy_X, dummy_y)
        
        # Save model
        model_dir = Path(settings.XGBOOST_MODEL_PATH)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        scoring_model.save_model(str(model_dir / "scoring_model.json"))
        self.models["scoring"] = scoring_model
        
        self.logger.info("Default XGBoost models created")
    
    async def _load_scalers(self, model_dir: Path) -> None:
        """Load feature scalers."""
        # Implementation would load saved scalers
        pass
    
    async def _load_feature_extractors(self, model_dir: Path) -> None:
        """Load feature extractors."""
        # Implementation would load saved feature extractors
        pass
    
    async def _prepare_feature_vector(self, features: Dict[str, Any]) -> np.ndarray:
        """Prepare feature vector for model input."""
        # Convert features to numpy array
        # This is a simplified implementation
        feature_values = []
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                feature_values.append(float(value))
            elif isinstance(value, (list, tuple)):
                feature_values.extend([float(v) for v in value])
            else:
                # Convert categorical to numeric
                feature_values.append(hash(str(value)) % 1000 / 1000.0)
        
        return np.array(feature_values).reshape(1, -1)
    
    def _extract_scoring_features(self, feature_vector: np.ndarray) -> np.ndarray:
        """Extract features for scoring model."""
        # For now, use all features
        return feature_vector
    
    def _extract_constraint_features(self, feature_vector: np.ndarray) -> np.ndarray:
        """Extract features for constraint model."""
        # For now, use all features
        return feature_vector
    
    async def _calculate_overall_score(self, predictions: Dict[str, float]) -> float:
        """Calculate overall score from individual predictions."""
        # Weighted combination of scores
        weights = {"score": 0.7, "constraint_satisfaction": 0.3}
        
        overall_score = 0.0
        for key, weight in weights.items():
            if key in predictions:
                overall_score += predictions[key] * weight
        
        return overall_score
    
    async def _calculate_confidence_intervals(
        self, feature_vector: np.ndarray, predictions: Dict[str, float]
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for predictions."""
        # Simplified implementation - would use model uncertainty in practice
        confidence_intervals = {}
        
        for key, value in predictions.items():
            if key != "prediction_time" and key != "model_version":
                # Assume 95% confidence interval with ±5% margin
                margin = abs(value) * 0.05
                confidence_intervals[key] = (value - margin, value + margin)
        
        return confidence_intervals


class FeatureEngineering:
    """Feature engineering utilities for optimization problems."""
    
    @staticmethod
    def create_spatial_features(
        spatial_constraints: List[SpatialConstraint],
    ) -> Dict[str, float]:
        """Create spatial features from constraints."""
        features = {}
        
        for i, constraint in enumerate(spatial_constraints):
            prefix = f"spatial_{i}_"
            
            # Distance features
            if constraint.operation == "distance":
                features[f"{prefix}distance"] = constraint.buffer or 0.0
                features[f"{prefix}area"] = constraint.buffer ** 2 if constraint.buffer else 0.0
            
            # Geometry complexity features
            features[f"{prefix}srid"] = float(constraint.srid)
        
        return features
    
    @staticmethod
    def create_constraint_features(constraints: List[Constraint]) -> Dict[str, float]:
        """Create features from constraint definitions."""
        features = {
            "total_constraints": len(constraints),
            "hard_constraints": len([c for c in constraints if c.type == ConstraintType.HARD]),
            "soft_constraints": len([c for c in constraints if c.type == ConstraintType.SOFT]),
            "avg_constraint_weight": np.mean([c.weight for c in constraints]),
            "max_constraint_priority": max([c.priority for c in constraints], default=0),
        }
        
        return features
    
    @staticmethod
    def create_objective_features(objectives: List[Objective]) -> Dict[str, float]:
        """Create features from objective definitions."""
        features = {
            "num_objectives": len(objectives),
            "max_objective_weight": max([obj.weight for obj in objectives], default=0),
            "minimize_count": len([obj for obj in objectives if obj.type == "minimize"]),
            "maximize_count": len([obj for obj in objectives if obj.type == "maximize"]),
        }
        
        return features