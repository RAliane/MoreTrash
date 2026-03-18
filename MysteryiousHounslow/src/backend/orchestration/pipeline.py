"""
Pipeline stages for the optimization workflow.

This module implements the individual stages of the optimization pipeline,
each responsible for a specific part of the optimization process.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Removed SQLAlchemy import - using Hasura only

from src.backend.core.config import settings
from src.backend.core.exceptions import (
    ConstraintException,
    OptimizationException,
    ValidationException,
    WorkflowException,
)
from src.backend.core.models import (
    Constraint,
    ConstraintType,
    Microtask,
    OptimizationRequest,
    OptimizationStatus,
    Solution,
    SpatialConstraint,
)
from src.backend.database.hasura_client import HasuraClient

# Removed PostGISClient import - using Hasura only
from src.backend.optimization.constraint_solver import ConstraintSolver
from src.backend.optimization.genetic_optimizer import GeneticOptimizer
from src.backend.optimization.knn_service import KNNService
from src.backend.optimization.xgboost_engine import XGBoostEngine
from src.backend.infrastructure.logging_config import get_logger


class PipelineContext:
    """Context object for pipeline execution."""

    def __init__(
        self,
        request_id: str,
        request: OptimizationRequest,
        session: Optional[AsyncSession] = None,
    ):
        """
        Initialize pipeline context.

        Args:
            request_id: Request identifier
            request: Optimization request
            session: Database session
        """
        self.request_id = request_id
        self.request = request
        self.session = session

        # Execution state
        self.stage_completion: Dict[str, float] = {}
        self.microtasks: List[Microtask] = []
        self.solutions: List[Solution] = []
        self.errors: List[Exception] = []
        self.metadata: Dict[str, Any] = {"start_time": time.time()}

        # Initialize services
        self.hasura_client = HasuraClient()
        self.xgboost_engine = XGBoostEngine()
        self.genetic_optimizer = GeneticOptimizer()
        self.constraint_solver = ConstraintSolver()
        self.knn_service = KNNService()


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    def __init__(self, name: str, order: int):
        """
        Initialize pipeline stage.

        Args:
            name: Stage name
            order: Stage execution order
        """
        self.name = name
        self.order = order
        self.logger = get_logger(f"{__name__}.{name}")
        self.execution_states: Dict[str, str] = {}  # request_id -> status

    @abstractmethod
    async def execute(self, context: PipelineContext) -> None:
        """
        Execute the pipeline stage.

        Args:
            context: Pipeline execution context
        """
        pass

    def is_running(self, request_id: str) -> bool:
        """Check if stage is running for a request."""
        return self.execution_states.get(request_id) == "running"

    def is_completed(self, request_id: str) -> bool:
        """Check if stage is completed for a request."""
        return self.execution_states.get(request_id) == "completed"


class InputValidationStage(PipelineStage):
    """Stage for input validation."""

    def __init__(self):
        """Initialize input validation stage."""
        super().__init__("input_validation", 1)

    async def execute(self, context: PipelineContext) -> None:
        """Execute input validation."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Validate request structure
            if not context.request.name:
                raise ValidationException(
                    message="Optimization request must have a name",
                    field="name",
                )

            if not context.request.objectives:
                raise ValidationException(
                    message="At least one objective must be specified",
                    field="objectives",
                )

            if not context.request.variables:
                raise ValidationException(
                    message="At least one variable must be defined",
                    field="variables",
                )

            # Validate variable definitions
            for var_name, var_def in context.request.variables.items():
                await self._validate_variable(var_name, var_def)

            # Validate constraints
            for constraint in context.request.constraints:
                await self._validate_constraint(constraint)

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Input validation completed", extra={"request_id": context.request_id}
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _validate_variable(self, var_name: str, var_def: Dict[str, Any]) -> None:
        """Validate variable definition."""
        required_fields = ["type"]
        for field in required_fields:
            if field not in var_def:
                raise ValidationException(
                    message=f"Variable '{var_name}' missing required field '{field}'",
                    field=f"variables.{var_name}",
                )

        var_type = var_def["type"]
        valid_types = ["continuous", "integer", "binary", "categorical"]

        if var_type not in valid_types:
            raise ValidationException(
                message=f"Invalid variable type '{var_type}' for '{var_name}'",
                field=f"variables.{var_name}.type",
                value=var_type,
            )

    async def _validate_constraint(self, constraint: Constraint) -> None:
        """Validate constraint definition."""
        # Check that constraint has valid content
        content_fields = [
            "spatial_constraint",
            "temporal_constraint",
            "capacity_constraint",
            "mathematical_constraint",
        ]

        has_content = any(
            getattr(constraint, field) is not None for field in content_fields
        )

        if not has_content:
            raise ValidationException(
                message=f"Constraint '{constraint.name}' must have constraint content",
                field=f"constraints.{constraint.name}",
            )


class ConstraintValidationStage(PipelineStage):
    """Stage for constraint validation."""

    def __init__(self):
        """Initialize constraint validation stage."""
        super().__init__("constraint_validation", 2)

    async def execute(self, context: PipelineContext) -> None:
        """Execute constraint validation."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Separate hard and soft constraints
            hard_constraints = [
                c for c in context.request.constraints if c.type == ConstraintType.HARD
            ]
            soft_constraints = [
                c for c in context.request.constraints if c.type == ConstraintType.SOFT
            ]

            # Validate hard constraints
            for constraint in hard_constraints:
                await self._validate_hard_constraint(constraint, context)

            # Validate soft constraints
            for constraint in soft_constraints:
                await self._validate_soft_constraint(constraint, context)

            # Store constraint information in metadata
            context.metadata["hard_constraints"] = len(hard_constraints)
            context.metadata["soft_constraints"] = len(soft_constraints)

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Constraint validation completed",
                extra={
                    "request_id": context.request_id,
                    "hard_constraints": len(hard_constraints),
                    "soft_constraints": len(soft_constraints),
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _validate_hard_constraint(
        self, constraint: Constraint, context: PipelineContext
    ) -> None:
        """Validate a hard constraint."""
        if constraint.spatial_constraint:
            await self._validate_spatial_constraint(constraint.spatial_constraint)

        elif constraint.mathematical_constraint:
            await self._validate_mathematical_constraint(
                constraint.mathematical_constraint
            )

    async def _validate_soft_constraint(
        self, constraint: Constraint, context: PipelineContext
    ) -> None:
        """Validate a soft constraint."""
        # Soft constraints must have weights
        if constraint.weight <= 0:
            raise ValidationException(
                message=f"Soft constraint '{constraint.name}' must have positive weight",
                field=f"constraints.{constraint.name}.weight",
                value=constraint.weight,
            )

    async def _validate_spatial_constraint(self, constraint: SpatialConstraint) -> None:
        """Validate spatial constraint."""
        # Validate SRID
        if constraint.srid <= 0:
            raise ValidationException(
                message="Spatial constraint must have valid SRID",
                value=constraint.srid,
            )

    async def _validate_mathematical_constraint(
        self, constraint: MathematicalConstraint
    ) -> None:
        """Validate mathematical constraint."""
        valid_operators = ["<=", ">=", "==", "<", ">"]
        if constraint.operator not in valid_operators:
            raise ValidationException(
                message=f"Invalid constraint operator '{constraint.operator}'",
                value=constraint.operator,
            )


class HardConstraintEnforcementStage(PipelineStage):
    """Stage for enforcing hard constraints."""

    def __init__(self):
        """Initialize hard constraint enforcement stage."""
        super().__init__("hard_constraint_enforcement", 3)

    async def execute(self, context: PipelineContext) -> None:
        """Execute hard constraint enforcement."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Get hard constraints
            hard_constraints = [
                c for c in context.request.constraints if c.type == ConstraintType.HARD
            ]

            if not hard_constraints:
                self.logger.info(
                    "No hard constraints to enforce",
                    extra={"request_id": context.request_id},
                )
                context.stage_completion[self.name] = 100.0
                self.execution_states[context.request_id] = "completed"
                return

            # Process spatial constraints
            spatial_constraints = [c for c in hard_constraints if c.spatial_constraint]

            if spatial_constraints:
                await self._enforce_spatial_constraints(spatial_constraints, context)

            # Process mathematical constraints
            math_constraints = [
                c for c in hard_constraints if c.mathematical_constraint
            ]

            if math_constraints:
                await self._enforce_mathematical_constraints(math_constraints, context)

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Hard constraint enforcement completed",
                extra={
                    "request_id": context.request_id,
                    "constraints_enforced": len(hard_constraints),
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _enforce_spatial_constraints(
        self, constraints: List[Constraint], context: PipelineContext
    ) -> None:
        """Enforce spatial hard constraints using PostGIS."""
        for constraint in constraints:
            spatial_constraint = constraint.spatial_constraint

            # Use kNN service to validate spatial constraints
            violations = await context.knn_service.check_constraint_violations(
                spatial_constraint, context.request.variables
            )

            if violations:
                raise ConstraintException(
                    message=f"Spatial constraint '{constraint.name}' violated",
                    constraint_type="spatial",
                    constraint_details={
                        "constraint_name": constraint.name,
                        "violations": violations,
                    },
                )

    async def _enforce_mathematical_constraints(
        self, constraints: List[Constraint], context: PipelineContext
    ) -> None:
        """Enforce mathematical hard constraints using OR-Tools."""
        # Convert constraints to OR-Tools format
        ortools_constraints = []
        for constraint in constraints:
            math_constraint = constraint.mathematical_constraint
            ortools_constraints.append(
                {
                    "expression": math_constraint.expression,
                    "operator": math_constraint.operator,
                    "rhs": math_constraint.rhs,
                    "variables": math_constraint.variables,
                }
            )

        # Use constraint solver to check feasibility
        is_feasible = await context.constraint_solver.check_feasibility(
            ortools_constraints, context.request.variables
        )

        if not is_feasible:
            raise ConstraintException(
                message="Mathematical constraints are infeasible",
                constraint_type="mathematical",
                constraint_details={"constraints": len(constraints)},
            )


class SoftConstraintScoringStage(PipelineStage):
    """Stage for scoring soft constraints."""

    def __init__(self):
        """Initialize soft constraint scoring stage."""
        super().__init__("soft_constraint_scoring", 4)

    async def execute(self, context: PipelineContext) -> None:
        """Execute soft constraint scoring."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Get soft constraints
            soft_constraints = [
                c for c in context.request.constraints if c.type == ConstraintType.SOFT
            ]

            if not soft_constraints:
                self.logger.info(
                    "No soft constraints to score",
                    extra={"request_id": context.request_id},
                )
                context.stage_completion[self.name] = 100.0
                self.execution_states[context.request_id] = "completed"
                return

            # Score each soft constraint
            constraint_scores = {}

            for constraint in soft_constraints:
                score = await self._score_soft_constraint(constraint, context)
                constraint_scores[constraint.name] = score

            # Store scores in metadata
            context.metadata["constraint_scores"] = constraint_scores
            context.metadata["total_constraint_score"] = sum(constraint_scores.values())

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Soft constraint scoring completed",
                extra={
                    "request_id": context.request_id,
                    "constraints_scored": len(soft_constraints),
                    "total_score": context.metadata["total_constraint_score"],
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _score_soft_constraint(
        self, constraint: Constraint, context: PipelineContext
    ) -> float:
        """Score a single soft constraint."""
        # Base score calculation
        base_score = 1.0

        # Apply penalty based on constraint type
        if constraint.spatial_constraint:
            # Calculate spatial constraint satisfaction
            violations = await context.knn_service.check_constraint_violations(
                constraint.spatial_constraint, context.request.variables
            )
            penalty = len(violations) * 0.1  # 10% penalty per violation
            base_score -= penalty

        elif constraint.capacity_constraint:
            # Calculate capacity utilization
            capacity = constraint.capacity_constraint.capacity
            usage = constraint.capacity_constraint.current_usage
            utilization = usage / capacity if capacity > 0 else 1.0
            base_score -= (
                abs(1.0 - utilization) * 0.5
            )  # Penalty for over/under utilization

        # Apply weight
        weighted_score = base_score * constraint.weight

        return max(0.0, weighted_score)


class MLScoringStage(PipelineStage):
    """Stage for ML-based scoring using XGBoost."""

    def __init__(self):
        """Initialize ML scoring stage."""
        super().__init__("ml_scoring", 5)

    async def execute(self, context: PipelineContext) -> None:
        """Execute ML scoring."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Prepare features for XGBoost
            features = await self._prepare_features(context)

            # Get XGBoost predictions
            predictions = await context.xgboost_engine.predict(features)

            # Store predictions in metadata
            context.metadata["ml_predictions"] = predictions
            context.metadata["ml_score"] = predictions.get("overall_score", 0.0)

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "ML scoring completed",
                extra={
                    "request_id": context.request_id,
                    "ml_score": context.metadata["ml_score"],
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _prepare_features(self, context: PipelineContext) -> Dict[str, Any]:
        """Prepare features for XGBoost model."""
        # Extract features from request
        features = {
            "num_variables": len(context.request.variables),
            "num_objectives": len(context.request.objectives),
            "num_constraints": len(context.request.constraints),
            "hard_constraints": len(
                [
                    c
                    for c in context.request.constraints
                    if c.type == ConstraintType.HARD
                ]
            ),
            "soft_constraints": len(
                [
                    c
                    for c in context.request.constraints
                    if c.type == ConstraintType.SOFT
                ]
            ),
            "constraint_score": context.metadata.get("total_constraint_score", 0.0),
        }

        return features


class OptimizationStage(PipelineStage):
    """Stage for multi-objective optimization using PyGAD."""

    def __init__(self):
        """Initialize optimization stage."""
        super().__init__("optimization", 6)

    async def execute(self, context: PipelineContext) -> None:
        """Execute optimization."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Prepare optimization parameters
            optimization_params = {
                "variables": context.request.variables,
                "objectives": context.request.objectives,
                "constraints": context.request.constraints,
                "parameters": context.request.parameters,
            }

            # Run genetic optimization
            solutions = await context.genetic_optimizer.optimize(optimization_params)

            # Convert to Solution objects
            context.solutions = [
                Solution(
                    solution_id=f"{context.request_id}-{i}",
                    variables=sol.get("variables", {}),
                    objectives=sol.get("objectives", {}),
                    fitness_score=sol.get("fitness", 0.0),
                    is_feasible=sol.get("feasible", True),
                    rank=i + 1,
                    metadata=sol.get("metadata", {}),
                )
                for i, sol in enumerate(solutions)
            ]

            # Store optimization metadata
            context.metadata["num_solutions"] = len(context.solutions)
            context.metadata["convergence_history"] = (
                context.genetic_optimizer.get_convergence_history()
            )

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Optimization completed",
                extra={
                    "request_id": context.request_id,
                    "num_solutions": len(context.solutions),
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise


class SolutionValidationStage(PipelineStage):
    """Stage for solution validation."""

    def __init__(self):
        """Initialize solution validation stage."""
        super().__init__("solution_validation", 7)

    async def execute(self, context: PipelineContext) -> None:
        """Execute solution validation."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Validate each solution
            validation_results = []

            for solution in context.solutions:
                is_valid = await self._validate_solution(solution, context)
                validation_results.append(is_valid)

                # Update solution feasibility
                solution.is_feasible = is_valid

            # Calculate validation statistics
            valid_solutions = sum(validation_results)
            total_solutions = len(validation_results)
            validation_rate = (
                valid_solutions / total_solutions if total_solutions > 0 else 0.0
            )

            context.metadata["validation_rate"] = validation_rate
            context.metadata["valid_solutions"] = valid_solutions
            context.metadata["total_solutions"] = total_solutions

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Solution validation completed",
                extra={
                    "request_id": context.request_id,
                    "validation_rate": validation_rate,
                    "valid_solutions": valid_solutions,
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _validate_solution(
        self, solution: Solution, context: PipelineContext
    ) -> bool:
        """Validate a single solution."""
        # Check hard constraints
        hard_constraints = [
            c for c in context.request.constraints if c.type == ConstraintType.HARD
        ]

        for constraint in hard_constraints:
            if not await self._check_constraint_satisfaction(solution, constraint):
                return False

        return True

    async def _check_constraint_satisfaction(
        self, solution: Solution, constraint: Constraint
    ) -> bool:
        """Check if solution satisfies a constraint."""
        # Implementation depends on constraint type
        if constraint.mathematical_constraint:
            return self._check_mathematical_constraint(
                solution, constraint.mathematical_constraint
            )

        return True

    def _check_mathematical_constraint(
        self, solution: Solution, constraint: MathematicalConstraint
    ) -> bool:
        """Check mathematical constraint satisfaction."""
        # Simple implementation - would need proper expression evaluation
        # For now, assume all mathematical constraints are satisfied
        return True


class ResultAggregationStage(PipelineStage):
    """Stage for result aggregation and final processing."""

    def __init__(self):
        """Initialize result aggregation stage."""
        super().__init__("result_aggregation", 8)

    async def execute(self, context: PipelineContext) -> None:
        """Execute result aggregation."""
        self.execution_states[context.request_id] = "running"
        context.metadata["current_stage"] = self.name

        try:
            # Sort solutions by fitness score
            context.solutions.sort(key=lambda s: s.fitness_score, reverse=True)

            # Update ranks
            for i, solution in enumerate(context.solutions):
                solution.rank = i + 1

            # Calculate constraint satisfaction rates
            constraint_satisfaction = {}

            for constraint in context.request.constraints:
                satisfaction_rate = await self._calculate_constraint_satisfaction(
                    constraint, context.solutions
                )
                constraint_satisfaction[constraint.name] = satisfaction_rate

            context.metadata["constraint_satisfaction"] = constraint_satisfaction

            # Update stage completion
            context.stage_completion[self.name] = 100.0
            self.execution_states[context.request_id] = "completed"

            self.logger.info(
                "Result aggregation completed",
                extra={
                    "request_id": context.request_id,
                    "num_solutions": len(context.solutions),
                },
            )

        except Exception as exc:
            self.execution_states[context.request_id] = "failed"
            context.errors.append(exc)
            raise

    async def _calculate_constraint_satisfaction(
        self, constraint: Constraint, solutions: List[Solution]
    ) -> float:
        """Calculate satisfaction rate for a constraint."""
        if not solutions:
            return 0.0

        satisfied_count = sum(
            1
            for solution in solutions
            if constraint.name in solution.constraint_violations
            and solution.constraint_violations[constraint.name] == 0
        )

        return satisfied_count / len(solutions)
