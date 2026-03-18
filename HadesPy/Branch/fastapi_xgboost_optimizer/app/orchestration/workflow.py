"""
Optimization workflow orchestrator for the FastAPI XGBoost Optimizer.

This module implements the main workflow orchestration logic that coordinates
all stages of the optimization process from input validation to result delivery.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConstraintException,
    DatabaseException,
    OptimizationException,
    ValidationException,
    WorkflowException,
)
from app.core.models import (
    Microtask,
    MicrotaskStatus,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationStatus,
    Solution,
)
from app.infrastructure.logging_config import get_logger
from app.orchestration.microtasks import MicrotaskExecutor
from app.orchestration.pipeline import (
    ConstraintValidationStage,
    HardConstraintEnforcementStage,
    InputValidationStage,
    MLScoringStage,
    OptimizationStage,
    PipelineContext,
    PipelineStage,
    ResultAggregationStage,
    SolutionValidationStage,
    SoftConstraintScoringStage,
)


class OptimizationWorkflow:
    """
    Main optimization workflow orchestrator.
    
    Coordinates the entire optimization process from input validation
    through solution delivery.
    """
    
    def __init__(self):
        """Initialize the workflow orchestrator."""
        self.logger = get_logger(__name__)
        self.executor = MicrotaskExecutor()
        
        # Define pipeline stages
        self.stages = [
            InputValidationStage(),
            ConstraintValidationStage(),
            HardConstraintEnforcementStage(),
            SoftConstraintScoringStage(),
            MLScoringStage(),
            OptimizationStage(),
            SolutionValidationStage(),
            ResultAggregationStage(),
        ]
        
        self.logger.info("Optimization workflow initialized")
    
    async def execute(
        self,
        request: OptimizationRequest,
        request_id: str,
        session: Optional[AsyncSession] = None,
    ) -> OptimizationResponse:
        """
        Execute the complete optimization workflow.
        
        Args:
            request: Optimization request
            request_id: Unique request identifier
            session: Database session (optional)
            
        Returns:
            OptimizationResponse: Optimization results
            
        Raises:
            WorkflowException: If workflow execution fails
        """
        start_time = time.time()
        
        self.logger.info(
            "Starting optimization workflow",
            extra={
                "request_id": request_id,
                "problem_name": request.name,
                "num_variables": len(request.variables),
                "num_objectives": len(request.objectives),
                "num_constraints": len(request.constraints),
            }
        )
        
        # Create pipeline context
        context = PipelineContext(
            request_id=request_id,
            request=request,
            session=session,
            stage_completion={},
            microtasks=[],
            solutions=[],
            errors=[],
            metadata={},
        )
        
        try:
            # Execute pipeline stages
            for stage in self.stages:
                stage_start = time.time()
                
                self.logger.info(
                    f"Executing stage: {stage.name}",
                    extra={
                        "request_id": request_id,
                        "stage": stage.name,
                        "stage_order": stage.order,
                    }
                )
                
                # Execute stage
                await stage.execute(context)
                
                # Update stage completion
                stage_time = time.time() - stage_start
                context.stage_completion[stage.name] = 100.0
                
                self.logger.info(
                    f"Stage completed: {stage.name}",
                    extra={
                        "request_id": request_id,
                        "stage": stage.name,
                        "execution_time": stage_time,
                        "status": "success",
                    }
                )
                
                # Check for cancellation
                if context.metadata.get("cancelled", False):
                    self.logger.info(
                        "Workflow cancelled",
                        extra={"request_id": request_id}
                    )
                    break
            
            # Create final response
            execution_time = time.time() - start_time
            
            response = OptimizationResponse(
                request_id=request_id,
                status=OptimizationStatus.COMPLETED,
                solutions=context.solutions,
                best_solution=context.solutions[0] if context.solutions else None,
                execution_time=execution_time,
                stage_completion=context.stage_completion,
                convergence_history=context.metadata.get("convergence_history", []),
                constraint_satisfaction=context.metadata.get("constraint_satisfaction", {}),
                created_at=context.metadata.get("start_time", time.time()),
                metadata=context.metadata,
            )
            
            self.logger.info(
                "Optimization workflow completed successfully",
                extra={
                    "request_id": request_id,
                    "execution_time": execution_time,
                    "num_solutions": len(context.solutions),
                    "status": "success",
                }
            )
            
            return response
            
        except Exception as exc:
            # Log error
            execution_time = time.time() - start_time
            
            self.logger.error(
                "Optimization workflow failed",
                extra={
                    "request_id": request_id,
                    "execution_time": execution_time,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True
            )
            
            # Create error response
            error_response = OptimizationResponse(
                request_id=request_id,
                status=OptimizationStatus.FAILED,
                execution_time=execution_time,
                stage_completion=context.stage_completion,
                error={
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                    "details": {
                        "stage": context.metadata.get("current_stage", "unknown"),
                        "cause": getattr(exc, "cause", None),
                        "context": getattr(exc, "context", None),
                    }
                },
                created_at=context.metadata.get("start_time", time.time()),
                metadata=context.metadata,
            )
            
            return error_response
    
    async def cancel(self, request_id: str, session: Optional[AsyncSession] = None) -> None:
        """
        Cancel an ongoing optimization workflow.
        
        Args:
            request_id: Request ID to cancel
            session: Database session (optional)
        """
        self.logger.info(
            "Cancelling optimization workflow",
            extra={"request_id": request_id}
        )
        
        # Cancel all running microtasks
        await self.executor.cancel_all()
        
        self.logger.info(
            "Optimization workflow cancelled",
            extra={"request_id": request_id}
        )
    
    async def get_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow execution.
        
        Args:
            request_id: Request ID
            
        Returns:
            Dict[str, Any]: Workflow status information
        """
        # Get active microtasks
        active_tasks = await self.executor.get_active_tasks()
        
        # Calculate overall progress
        total_stages = len(self.stages)
        completed_stages = sum(1 for stage in self.stages if stage.is_completed(request_id))
        progress = (completed_stages / total_stages) * 100 if total_stages > 0 else 0
        
        return {
            "request_id": request_id,
            "progress": progress,
            "active_tasks": len(active_tasks),
            "completed_stages": completed_stages,
            "total_stages": total_stages,
            "current_stage": self._get_current_stage(request_id),
        }
    
    def _get_current_stage(self, request_id: str) -> Optional[str]:
        """Get the currently executing stage for a request."""
        for stage in self.stages:
            if stage.is_running(request_id):
                return stage.name
        return None


class BatchOptimizationWorkflow:
    """
    Batch optimization workflow for processing multiple requests.
    """
    
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize batch workflow.
        
        Args:
            max_concurrent: Maximum concurrent optimizations
        """
        self.max_concurrent = max_concurrent
        self.logger = get_logger(__name__)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_batch(
        self,
        requests: List[OptimizationRequest],
        batch_id: str,
        session: Optional[AsyncSession] = None,
    ) -> List[OptimizationResponse]:
        """
        Execute multiple optimization requests concurrently.
        
        Args:
            requests: List of optimization requests
            batch_id: Batch identifier
            session: Database session (optional)
            
        Returns:
            List[OptimizationResponse]: List of optimization results
        """
        self.logger.info(
            "Starting batch optimization workflow",
            extra={
                "batch_id": batch_id,
                "num_requests": len(requests),
                "max_concurrent": self.max_concurrent,
            }
        )
        
        # Create individual workflow instances
        workflow = OptimizationWorkflow()
        
        # Process requests concurrently with semaphore
        async def process_single_request(
            request: OptimizationRequest, index: int
        ) -> OptimizationResponse:
            async with self.semaphore:
                request_id = f"{batch_id}-{index}"
                return await workflow.execute(request, request_id, session)
        
        # Create tasks
        tasks = [
            process_single_request(request, idx)
            for idx, request in enumerate(requests)
        ]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        responses = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error response
                error_response = OptimizationResponse(
                    request_id=f"{batch_id}-{idx}",
                    status=OptimizationStatus.FAILED,
                    execution_time=0.0,
                    error={
                        "code": type(result).__name__.upper(),
                        "message": str(result),
                        "details": {"index": idx},
                    },
                )
                responses.append(error_response)
            else:
                responses.append(result)
        
        self.logger.info(
            "Batch optimization workflow completed",
            extra={
                "batch_id": batch_id,
                "num_requests": len(requests),
                "successful": sum(1 for r in responses if r.status == OptimizationStatus.COMPLETED),
                "failed": sum(1 for r in responses if r.status == OptimizationStatus.FAILED),
            }
        )
        
        return responses


class WorkflowMonitor:
    """
    Monitor for tracking workflow execution and performance.
    """
    
    def __init__(self):
        """Initialize workflow monitor."""
        self.logger = get_logger(__name__)
        self.active_workflows = {}
        self.completed_workflows = {}
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
        }
    
    def start_workflow(self, request_id: str, request: OptimizationRequest) -> None:
        """
        Record workflow start.
        
        Args:
            request_id: Request identifier
            request: Optimization request
        """
        self.active_workflows[request_id] = {
            "start_time": time.time(),
            "request": request,
            "stages": {},
        }
        
        self.metrics["total_executions"] += 1
        
        self.logger.info(
            "Workflow monitoring started",
            extra={"request_id": request_id}
        )
    
    def complete_workflow(
        self, request_id: str, status: OptimizationStatus, execution_time: float
    ) -> None:
        """
        Record workflow completion.
        
        Args:
            request_id: Request identifier
            status: Final workflow status
            execution_time: Total execution time
        """
        if request_id in self.active_workflows:
            workflow_data = self.active_workflows.pop(request_id)
            
            self.completed_workflows[request_id] = {
                **workflow_data,
                "end_time": time.time(),
                "status": status,
                "execution_time": execution_time,
            }
            
            # Update metrics
            if status == OptimizationStatus.COMPLETED:
                self.metrics["successful_executions"] += 1
            else:
                self.metrics["failed_executions"] += 1
            
            # Update average execution time
            total_time = (
                self.metrics["average_execution_time"] * (self.metrics["total_executions"] - 1)
                + execution_time
            ) / self.metrics["total_executions"]
            self.metrics["average_execution_time"] = total_time
            
            self.logger.info(
                "Workflow monitoring completed",
                extra={
                    "request_id": request_id,
                    "status": status,
                    "execution_time": execution_time,
                }
            )
    
    def record_stage_start(self, request_id: str, stage_name: str) -> None:
        """
        Record stage start.
        
        Args:
            request_id: Request identifier
            stage_name: Stage name
        """
        if request_id in self.active_workflows:
            self.active_workflows[request_id]["stages"][stage_name] = {
                "start_time": time.time(),
                "status": "running",
            }
    
    def record_stage_complete(
        self, request_id: str, stage_name: str, execution_time: float
    ) -> None:
        """
        Record stage completion.
        
        Args:
            request_id: Request identifier
            stage_name: Stage name
            execution_time: Stage execution time
        """
        if request_id in self.active_workflows:
            self.active_workflows[request_id]["stages"][stage_name].update({
                "end_time": time.time(),
                "status": "completed",
                "execution_time": execution_time,
            })
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
        }
    
    def get_workflow_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        if request_id in self.active_workflows:
            return {
                "status": "active",
                **self.active_workflows[request_id],
            }
        elif request_id in self.completed_workflows:
            return {
                "status": "completed",
                **self.completed_workflows[request_id],
            }
        
        return None


# Global workflow monitor
workflow_monitor = WorkflowMonitor()