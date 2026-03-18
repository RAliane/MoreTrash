from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import structlog

from app.core.schemas import (
    OptimizationRequest,
    OptimizationResponse,
    Solution,
    StageCompletion,
    ConvergenceHistory,
)
from app.orchestration.microtasks import (
    InputValidationTask,
    ConstraintValidationTask,
    HardConstraintEnforcementTask,
    SoftConstraintScoringTask,
    MLScoringTask,
    OptimizationTask,
    SolutionValidationTask,
    ResultAggregationTask,
)
from app.infrastructure.cache import RedisCache
from app.infrastructure.metrics import metrics
from app.infrastructure.logging import get_optimization_logger

logger = get_optimization_logger()


class OptimizationWorkflow:
    """Main workflow orchestrator for optimization requests."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.cache = RedisCache()
        self.logger = logger.bind(request_id=request_id)
        self.start_time = None
        self.stage_completion = StageCompletion(
            input_validation=0.0,
            constraint_validation=0.0,
            hard_constraint_enforcement=0.0,
            soft_constraint_scoring=0.0,
            ml_scoring=0.0,
            optimization=0.0,
            solution_validation=0.0,
            result_aggregation=0.0,
        )

    async def process_request(self, request: OptimizationRequest) -> None:
        """Process an optimization request through all stages."""
        self.start_time = datetime.utcnow()

        try:
            # Update status to processing
            await self._update_status("processing", progress=0.0)

            # Execute workflow stages
            result = await self._execute_workflow(request)

            # Update final status
            await self._update_status("completed", progress=100.0)
            await self._store_results(result)

            self.logger.info(
                "Optimization completed successfully",
                execution_time=(datetime.utcnow() - self.start_time).total_seconds(),
            )

        except Exception as e:
            self.logger.error("Optimization failed", error=str(e), exc_info=True)
            await self._update_status("failed", error=str(e))
            raise

    async def _execute_workflow(
        self, request: OptimizationRequest
    ) -> OptimizationResponse:
        """Execute the complete optimization workflow."""
        # Stage 1: Input Validation
        await self._update_stage_progress("input_validation", 100.0)
        validation_task = InputValidationTask()
        validated_request = await validation_task.execute(request)

        # Stage 2: Constraint Validation
        await self._update_stage_progress("constraint_validation", 100.0)
        constraint_task = ConstraintValidationTask()
        validated_constraints = await constraint_task.execute(validated_request)

        # Stage 3: Hard Constraint Enforcement
        await self._update_stage_progress("hard_constraint_enforcement", 100.0)
        hard_constraint_task = HardConstraintEnforcementTask()
        feasible_region = await hard_constraint_task.execute(validated_constraints)

        # Stage 4: Soft Constraint Scoring
        await self._update_stage_progress("soft_constraint_scoring", 100.0)
        soft_constraint_task = SoftConstraintScoringTask()
        scored_constraints = await soft_constraint_task.execute(feasible_region)

        # Stage 5: ML Scoring
        await self._update_stage_progress("ml_scoring", 100.0)
        ml_task = MLScoringTask()
        ml_scores = await ml_task.execute(scored_constraints)

        # Stage 6: Optimization
        await self._update_stage_progress("optimization", 50.0)
        optimization_task = OptimizationTask()
        optimization_result = await optimization_task.execute(ml_scores)
        await self._update_stage_progress("optimization", 100.0)

        # Stage 7: Solution Validation
        await self._update_stage_progress("solution_validation", 100.0)
        validation_task = SolutionValidationTask()
        validated_solutions = await validation_task.execute(optimization_result)

        # Stage 8: Result Aggregation
        await self._update_stage_progress("result_aggregation", 100.0)
        aggregation_task = ResultAggregationTask()
        final_result = await aggregation_task.execute(validated_solutions)

        return final_result

    async def _update_status(
        self,
        status: str,
        progress: float = None,
        current_stage: str = None,
        error: str = None,
    ) -> None:
        """Update optimization status in cache."""
        status_data = {
            "request_id": self.request_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if progress is not None:
            status_data["progress"] = progress
        if current_stage:
            status_data["current_stage"] = current_stage
        if error:
            status_data["error"] = error

        await self.cache.set(f"optimization:{self.request_id}:status", status_data)

    async def _update_stage_progress(self, stage: str, progress: float) -> None:
        """Update progress for a specific stage."""
        setattr(self.stage_completion, stage, progress)

        # Update overall status
        total_progress = (
            sum(
                [
                    self.stage_completion.input_validation,
                    self.stage_completion.constraint_validation,
                    self.stage_completion.hard_constraint_enforcement,
                    self.stage_completion.soft_constraint_scoring,
                    self.stage_completion.ml_scoring,
                    self.stage_completion.optimization,
                    self.stage_completion.solution_validation,
                    self.stage_completion.result_aggregation,
                ]
            )
            / 8.0
        )

        await self._update_status(
            "processing", progress=total_progress, current_stage=stage
        )

    async def _store_results(self, result: OptimizationResponse) -> None:
        """Store optimization results in cache."""
        result_data = result.dict()
        result_data["stage_completion"] = self.stage_completion.dict()

        await self.cache.set(
            f"optimization:{self.request_id}:results",
            result_data,
            ttl=86400,  # 24 hours
        )
