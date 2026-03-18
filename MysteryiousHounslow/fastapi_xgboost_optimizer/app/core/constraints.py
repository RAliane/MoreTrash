from typing import List, Dict, Any, Optional, Protocol
import structlog

from app.core.models import Constraint, Variable, OptimizationProblem
from app.infrastructure.logging import get_optimization_logger

logger = get_optimization_logger()


class ConstraintEvaluator(Protocol):
    """Protocol for constraint evaluation."""

    def evaluate(self, variables: Dict[str, Any]) -> float:
        """Evaluate constraint violation. Returns 0 for satisfied, >0 for violation."""
        ...


class ExpressionConstraintEvaluator:
    """Evaluates constraints defined by mathematical expressions."""

    def __init__(self, expression: str, variables: List[str]):
        self.expression = expression
        self.variables = variables

    def evaluate(self, variable_values: Dict[str, Any]) -> float:
        """Evaluate expression-based constraint."""
        try:
            # Simple evaluation for basic expressions
            # In production, use a safe expression evaluator
            expr = self.expression

            # Substitute variable values
            for var in self.variables:
                if var in variable_values:
                    expr = expr.replace(var, str(variable_values[var]))

            # For now, return mock evaluation
            # In real implementation, use sympy or similar
            return 0.0  # Mock: constraint satisfied

        except Exception as e:
            logger.warning(
                "Constraint evaluation failed", expression=self.expression, error=str(e)
            )
            return float("inf")  # Constraint violated


class SpatialConstraintEvaluator:
    """Evaluates spatial constraints using PostGIS."""

    def __init__(self, spatial_data: Dict[str, Any]):
        self.spatial_data = spatial_data

    def evaluate(self, variable_values: Dict[str, Any]) -> float:
        """Evaluate spatial constraint."""
        try:
            # For now, return mock spatial evaluation
            # In real implementation, query PostGIS
            return 0.0  # Mock: spatial constraint satisfied

        except Exception as e:
            logger.warning("Spatial constraint evaluation failed", error=str(e))
            return float("inf")


class ConstraintProcessor:
    """Processes and validates optimization constraints."""

    def __init__(self):
        self.logger = logger.bind(component="constraint_processor")

    def process_constraints(
        self, constraints: List[Constraint], variables: List[Variable]
    ) -> Dict[str, ConstraintEvaluator]:
        """Process constraints and create evaluators."""
        evaluators = {}

        for constraint in constraints:
            try:
                if constraint.expression:
                    evaluator = ExpressionConstraintEvaluator(
                        constraint.expression, [v.name for v in variables]
                    )
                elif constraint.spatial_constraint:
                    evaluator = SpatialConstraintEvaluator(
                        constraint.spatial_constraint
                    )
                else:
                    self.logger.warning(
                        "Constraint has no evaluation method",
                        constraint_name=constraint.name,
                    )
                    continue

                evaluators[constraint.name] = evaluator

            except Exception as e:
                self.logger.error(
                    "Failed to create constraint evaluator",
                    constraint_name=constraint.name,
                    error=str(e),
                )
                continue

        self.logger.info(
            "Constraint processing completed",
            total_constraints=len(constraints),
            valid_evaluators=len(evaluators),
        )

        return evaluators

    def validate_feasibility(
        self,
        variable_values: Dict[str, Any],
        evaluators: Dict[str, ConstraintEvaluator],
        constraint_types: Dict[str, str],
    ) -> Dict[str, float]:
        """Validate solution feasibility against constraints."""
        violations = {}

        for constraint_name, evaluator in evaluators.items():
            violation_score = evaluator.evaluate(variable_values)
            violations[constraint_name] = violation_score

            constraint_type = constraint_types.get(constraint_name, "soft")

            if constraint_type == "hard" and violation_score > 0:
                self.logger.debug(
                    "Hard constraint violated",
                    constraint=constraint_name,
                    violation=violation_score,
                )

        return violations

    def calculate_constraint_score(
        self, violations: Dict[str, float], constraint_weights: Dict[str, float]
    ) -> float:
        """Calculate overall constraint satisfaction score."""
        total_score = 0.0
        total_weight = 0.0

        for constraint_name, violation in violations.items():
            weight = constraint_weights.get(constraint_name, 1.0)
            # Convert violation to satisfaction score (higher is better)
            satisfaction = max(0, 1.0 - violation)
            total_score += satisfaction * weight
            total_weight += weight

        if total_weight == 0:
            return 1.0

        return total_score / total_weight

    def separate_constraints(self, constraints: List[Constraint]) -> tuple:
        """Separate hard and soft constraints."""
        hard_constraints = []
        soft_constraints = []

        for constraint in constraints:
            if constraint.type == "hard":
                hard_constraints.append(constraint)
            else:
                soft_constraints.append(constraint)

        return hard_constraints, soft_constraints

    def get_constraint_metadata(self, constraints: List[Constraint]) -> Dict[str, Any]:
        """Extract metadata from constraints."""
        return {
            "total_constraints": len(constraints),
            "hard_constraints": len([c for c in constraints if c.type == "hard"]),
            "soft_constraints": len([c for c in constraints if c.type == "soft"]),
            "spatial_constraints": len(
                [c for c in constraints if c.spatial_constraint]
            ),
            "expression_constraints": len([c for c in constraints if c.expression]),
        }
