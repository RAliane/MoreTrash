"""
Microtask executor for atomic, deterministic operations.

This module implements the microtask execution engine that ensures
all operations are atomic, deterministic, and can be retried.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import WorkflowException
from app.core.models import Microtask, MicrotaskStatus
from app.infrastructure.logging_config import get_logger

T = TypeVar("T")


class MicrotaskExecutor:
    """
    Executor for atomic microtasks with retry and monitoring capabilities.
    
    Ensures all microtasks are:
    - Atomic: Either fully completed or not executed at all
    - Deterministic: Same input always produces same output
    - Retryable: Can be safely retried on failure
    - Observable: Full execution tracking and monitoring
    """
    
    def __init__(self):
        """Initialize the microtask executor."""
        self.logger = get_logger(__name__)
        self.active_tasks: Dict[str, Microtask] = {}
        self.task_history: Dict[str, List[Microtask]] = {}
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff
        
        self.logger.info("Microtask executor initialized")
    
    def create_task(
        self,
        name: str,
        task_type: str,
        parameters: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
    ) -> Microtask:
        """
        Create a new microtask.
        
        Args:
            name: Task name
            task_type: Task type/category
            parameters: Task parameters
            dependencies: List of dependent task IDs
            
        Returns:
            Microtask: Created microtask
        """
        # Generate deterministic task ID based on parameters
        task_data = {
            "name": name,
            "task_type": task_type,
            "parameters": parameters,
            "dependencies": dependencies or [],
        }
        
        task_id = self._generate_task_id(task_data)
        
        microtask = Microtask(
            id=task_id,
            name=name,
            task_type=task_type,
            parameters=parameters,
            dependencies=dependencies or [],
            status=MicrotaskStatus.PENDING,
        )
        
        self.logger.debug(
            "Microtask created",
            extra={
                "task_id": task_id,
                "name": name,
                "task_type": task_type,
                "num_dependencies": len(dependencies or []),
            }
        )
        
        return microtask
    
    async def execute_task(
        self,
        task: Microtask,
        executor_func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute a microtask with retry logic.
        
        Args:
            task: Microtask to execute
            executor_func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            T: Task execution result
            
        Raises:
            WorkflowException: If task execution fails after all retries
        """
        # Check if already executed
        if task.id in self.task_history:
            # Return cached result if task is deterministic
            cached_result = self._get_cached_result(task)
            if cached_result is not None:
                self.logger.debug(
                    "Returning cached result for deterministic task",
                    extra={"task_id": task.id}
                )
                return cached_result
        
        # Add to active tasks
        self.active_tasks[task.id] = task
        task.status = MicrotaskStatus.RUNNING
        task.started_at = time.time()
        
        self.logger.info(
            "Executing microtask",
            extra={
                "task_id": task.id,
                "name": task.name,
                "task_type": task.task_type,
            }
        )
        
        # Execute with retry logic
        last_exception = None
        
        for attempt in range(settings.MICROTASK_RETRY_ATTEMPTS):
            try:
                # Execute the task
                start_time = time.time()
                result = await executor_func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Update task status
                task.status = MicrotaskStatus.COMPLETED
                task.result = {"result": result, "execution_time": execution_time}
                task.completed_at = time.time()
                task.execution_time = execution_time
                
                # Cache result for deterministic tasks
                self._cache_result(task, result)
                
                # Remove from active tasks
                del self.active_tasks[task.id]
                
                self.logger.info(
                    "Microtask completed successfully",
                    extra={
                        "task_id": task.id,
                        "name": task.name,
                        "execution_time": execution_time,
                        "attempt": attempt + 1,
                    }
                )
                
                return result
                
            except Exception as exc:
                last_exception = exc
                
                self.logger.warning(
                    "Microtask execution failed",
                    extra={
                        "task_id": task.id,
                        "name": task.name,
                        "attempt": attempt + 1,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                )
                
                # Retry with exponential backoff (except last attempt)
                if attempt < settings.MICROTASK_RETRY_ATTEMPTS - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    await asyncio.sleep(delay)
        
        # All retries failed
        task.status = MicrotaskStatus.FAILED
        task.error = str(last_exception)
        task.completed_at = time.time()
        
        # Remove from active tasks
        del self.active_tasks[task.id]
        
        self.logger.error(
            "Microtask failed after all retries",
            extra={
                "task_id": task.id,
                "name": task.name,
                "error": str(last_exception),
                "error_type": type(last_exception).__name__,
            }
        )
        
        raise WorkflowException(
            message=f"Microtask '{task.name}' failed after {settings.MICROTASK_RETRY_ATTEMPTS} attempts",
            code="MICROTASK_EXECUTION_FAILED",
            cause=str(last_exception),
            context=f"Task execution for {task.name}",
            details={"task_id": task.id, "attempts": settings.MICROTASK_RETRY_ATTEMPTS},
        )
    
    async def execute_task_sync(
        self,
        task: Microtask,
        executor_func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute a microtask synchronously (for CPU-bound tasks).
        
        Args:
            task: Microtask to execute
            executor_func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            T: Task execution result
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.execute_task, task, executor_func, *args, **kwargs
        )
    
    async def execute_batch(
        self,
        tasks: List[Microtask],
        executor_funcs: List[Callable],
        max_concurrent: int = 10,
    ) -> List[Any]:
        """
        Execute multiple microtasks concurrently.
        
        Args:
            tasks: List of microtasks to execute
            executor_funcs: List of executor functions (parallel to tasks)
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List[Any]: List of execution results
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single_task(
            task: Microtask, executor_func: Callable, index: int
        ) -> Any:
            async with semaphore:
                try:
                    result = await self.execute_task(
                        task, executor_func, *task.parameters.get("args", []),
                        **task.parameters.get("kwargs", {})
                    )
                    return {"index": index, "result": result, "error": None}
                except Exception as exc:
                    return {"index": index, "result": None, "error": str(exc)}
        
        # Create tasks
        execution_tasks = [
            execute_single_task(task, executor_func, idx)
            for idx, (task, executor_func) in enumerate(zip(tasks, executor_funcs))
        ]
        
        # Execute all tasks
        results = await asyncio.gather(*execution_tasks)
        
        # Sort by original index and extract results
        results.sort(key=lambda x: x["index"])
        
        return [result["result"] for result in results]
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running microtask.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = MicrotaskStatus.FAILED
            task.error = "Task cancelled"
            task.completed_at = time.time()
            
            del self.active_tasks[task_id]
            
            self.logger.info(
                "Microtask cancelled",
                extra={"task_id": task_id}
            )
            
            return True
        
        return False
    
    async def cancel_all(self) -> None:
        """Cancel all running microtasks."""
        task_ids = list(self.active_tasks.keys())
        
        for task_id in task_ids:
            await self.cancel_task(task_id)
        
        self.logger.info(
            "All microtasks cancelled",
            extra={"num_cancelled": len(task_ids)}
        )
    
    def get_active_tasks(self) -> List[Microtask]:
        """Get list of currently active tasks."""
        return list(self.active_tasks.values())
    
    def get_task_history(self, task_id: str) -> List[Microtask]:
        """Get execution history for a task."""
        return self.task_history.get(task_id, [])
    
    def get_task_metrics(self) -> Dict[str, Any]:
        """Get task execution metrics."""
        active_count = len(self.active_tasks)
        
        # Calculate statistics from completed tasks
        completed_tasks = []
        for history in self.task_history.values():
            completed_tasks.extend([task for task in history if task.status == MicrotaskStatus.COMPLETED])
        
        if completed_tasks:
            avg_execution_time = sum(
                task.execution_time or 0 for task in completed_tasks
            ) / len(completed_tasks)
            min_execution_time = min(task.execution_time or 0 for task in completed_tasks)
            max_execution_time = max(task.execution_time or 0 for task in completed_tasks)
        else:
            avg_execution_time = min_execution_time = max_execution_time = 0.0
        
        return {
            "active_tasks": active_count,
            "completed_tasks": len(completed_tasks),
            "average_execution_time": avg_execution_time,
            "min_execution_time": min_execution_time,
            "max_execution_time": max_execution_time,
        }
    
    def _generate_task_id(self, task_data: Dict[str, Any]) -> str:
        """Generate deterministic task ID."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(task_data, sort_keys=True)
        
        # Generate hash
        task_hash = hashlib.sha256(sorted_data.encode()).hexdigest()
        
        return f"task_{task_hash[:16]}"
    
    def _get_cached_result(self, task: Microtask) -> Optional[Any]:
        """Get cached result for a deterministic task."""
        if task.id not in self.task_history:
            return None
        
        # Get the last successful execution
        for historical_task in reversed(self.task_history[task.id]):
            if historical_task.status == MicrotaskStatus.COMPLETED and historical_task.result:
                return historical_task.result.get("result")
        
        return None
    
    def _cache_result(self, task: Microtask, result: Any) -> None:
        """Cache result for deterministic tasks."""
        if task.id not in self.task_history:
            self.task_history[task.id] = []
        
        self.task_history[task.id].append(task)
        
        # Keep only last 10 executions per task
        if len(self.task_history[task.id]) > 10:
            self.task_history[task.id] = self.task_history[task.id][-10:]


# Predefined microtask types for common operations
class MicrotaskTypes:
    """Standard microtask type definitions."""
    
    # Validation tasks
    VALIDATE_INPUT = "validate_input"
    VALIDATE_CONSTRAINTS = "validate_constraints"
    
    # Constraint tasks
    ENFORCE_HARD_CONSTRAINTS = "enforce_hard_constraints"
    SCORE_SOFT_CONSTRAINTS = "score_soft_constraints"
    
    # ML tasks
    XGBOOST_SCORING = "xgboost_scoring"
    FEATURE_ENGINEERING = "feature_engineering"
    
    # Optimization tasks
    GENETIC_OPTIMIZATION = "genetic_optimization"
    CONSTRAINT_SOLVING = "constraint_solving"
    SOLUTION_VALIDATION = "solution_validation"
    
    # Database tasks
    DATABASE_QUERY = "database_query"
    DATA_PERSISTENCE = "data_persistence"
    
    # Utility tasks
    DATA_TRANSFORMATION = "data_transformation"
    METRICS_CALCULATION = "metrics_calculation"