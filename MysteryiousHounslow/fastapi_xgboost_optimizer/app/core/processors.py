from typing import Dict, List, Any, Optional
import numpy as np
import structlog

from app.core.models import Variable, Objective, OptimizationProblem
from app.infrastructure.logging import get_optimization_logger

logger = get_optimization_logger()


class DataProcessor:
    """Processes and transforms optimization data."""

    def __init__(self):
        self.logger = logger.bind(component="data_processor")

    def normalize_variables(
        self, variables: List[Variable], bounds: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Normalize variable bounds for optimization algorithms."""
        normalized = {}

        for var in variables:
            if var.type in ["continuous", "integer"]:
                var_bounds = bounds.get(var.name, [0, 1000])
                # Normalize to [0, 1] range
                normalized[var.name] = {
                    "original_bounds": var_bounds,
                    "normalized_bounds": [0, 1],
                    "scale": var_bounds[1] - var_bounds[0],
                    "offset": var_bounds[0],
                }
            else:
                # Categorical variables remain unchanged
                normalized[var.name] = {
                    "type": "categorical",
                    "categories": var.categories or [],
                }

        self.logger.debug(
            "Variable normalization completed", variables_processed=len(variables)
        )
        return normalized

    def denormalize_solution(
        self, normalized_solution: Dict[str, Any], normalization_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert normalized solution back to original scale."""
        denormalized = {}

        for var_name, value in normalized_solution.items():
            if var_name in normalization_info:
                info = normalization_info[var_name]
                if info.get("type") == "categorical":
                    denormalized[var_name] = value
                else:
                    # Denormalize continuous/integer variables
                    scale = info["scale"]
                    offset = info["offset"]
                    denormalized[var_name] = value * scale + offset
            else:
                denormalized[var_name] = value

        return denormalized

    def validate_objective_functions(
        self, objectives: List[Objective], variables: List[Variable]
    ) -> List[str]:
        """Validate objective function expressions."""
        errors = []
        variable_names = {v.name for v in variables}

        for obj in objectives:
            # Check if all variables in objective are defined
            obj_vars = set()
            # Simple parsing - in production use proper expression parser
            for var in variable_names:
                if var in obj.function:
                    obj_vars.add(var)

            if not obj_vars:
                errors.append(f"Objective '{obj.name}' uses no defined variables")

            # Check for undefined variables
            for var in obj.variables or []:
                if var not in variable_names:
                    errors.append(
                        f"Objective '{obj.name}' references undefined variable '{var}'"
                    )

        if errors:
            self.logger.warning("Objective validation found errors", errors=errors)
        else:
            self.logger.debug("Objective validation completed successfully")

        return errors

    def prepare_ml_features(
        self,
        solution: Dict[str, Any],
        objectives: List[Objective],
        constraints: List[Dict[str, Any]],
    ) -> np.ndarray:
        """Prepare feature vector for ML scoring."""
        features = []

        # Add variable values
        for key, value in sorted(solution.items()):
            if isinstance(value, (int, float)):
                features.append(float(value))

        # Add objective values (if available)
        for obj in objectives:
            obj_value = solution.get(f"obj_{obj.name}", 0.0)
            features.append(float(obj_value))

        # Add constraint satisfaction scores
        for constraint in constraints:
            score = constraint.get("satisfaction_score", 0.0)
            features.append(float(score))

        feature_array = np.array(features).reshape(1, -1)

        self.logger.debug(
            "ML features prepared",
            feature_count=len(features),
            feature_shape=feature_array.shape,
        )

        return feature_array

    def calculate_objective_values(
        self, solution: Dict[str, Any], objectives: List[Objective]
    ) -> Dict[str, float]:
        """Calculate objective function values for a solution."""
        objective_values = {}

        for obj in objectives:
            try:
                # Simple evaluation - in production use safe evaluator
                value = self._evaluate_expression(obj.function, solution)
                objective_values[obj.name] = value

            except Exception as e:
                self.logger.warning(
                    "Objective evaluation failed", objective=obj.name, error=str(e)
                )
                objective_values[obj.name] = (
                    float("inf") if obj.type == "minimize" else float("-inf")
                )

        return objective_values

    def _evaluate_expression(self, expression: str, variables: Dict[str, Any]) -> float:
        """Safely evaluate mathematical expression."""
        # Very basic implementation - in production use sympy or asteval
        try:
            # Replace variable names with values
            eval_expr = expression
            for var_name, var_value in variables.items():
                if isinstance(var_value, (int, float)):
                    eval_expr = eval_expr.replace(var_name, str(var_value))

            # Use Python's eval with restricted globals/locals
            allowed_names = {
                k: v for k, v in variables.items() if isinstance(v, (int, float))
            }

            result = eval(eval_expr, {"__builtins__": {}}, allowed_names)
            return float(result)

        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {e}")

    def aggregate_results(
        self, solutions: List[Dict[str, Any]], objectives: List[Objective]
    ) -> Dict[str, Any]:
        """Aggregate optimization results."""
        if not solutions:
            return {"best_solution": None, "statistics": {}}

        # Find best solution based on weighted objectives
        best_solution = min(
            solutions, key=lambda s: self._calculate_weighted_score(s, objectives)
        )

        # Calculate statistics
        objective_values = [s.get("objectives", {}) for s in solutions]
        statistics = self._calculate_statistics(objective_values)

        return {
            "best_solution": best_solution,
            "statistics": statistics,
            "total_solutions": len(solutions),
        }

    def _calculate_weighted_score(
        self, solution: Dict[str, Any], objectives: List[Objective]
    ) -> float:
        """Calculate weighted objective score."""
        score = 0.0
        objectives_data = solution.get("objectives", {})

        for obj in objectives:
            obj_value = objectives_data.get(obj.name, 0.0)
            # Normalize based on objective type
            if obj.type == "minimize":
                normalized_value = obj_value
            else:
                normalized_value = -obj_value  # Maximize becomes minimize

            score += normalized_value * obj.weight

        return score

    def _calculate_statistics(
        self, objective_values: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate statistical measures for objectives."""
        if not objective_values:
            return {}

        stats = {}
        obj_names = set()

        for obj_dict in objective_values:
            obj_names.update(obj_dict.keys())

        for obj_name in obj_names:
            values = [
                obj.get(obj_name, 0.0) for obj in objective_values if obj_name in obj
            ]
            if values:
                stats[obj_name] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "count": len(values),
                }

        return stats
