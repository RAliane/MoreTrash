"""
Core business models and data structures for the FastAPI XGBoost Optimizer.

This module defines the domain models used throughout the application,
including optimization requests, constraints, solutions, and metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from shapely.geometry import Point, Polygon


class ConstraintType(str, Enum):
    """Types of constraints supported by the optimizer."""
    HARD = "hard"
    SOFT = "soft"


class OptimizationStatus(str, Enum):
    """Status of optimization workflow execution."""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MicrotaskStatus(str, Enum):
    """Status of individual microtask execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(str, Enum):
    """Log levels for structured logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpatialConstraint(BaseModel):
    """Spatial constraint definition."""
    type: str = Field(description="Type of spatial constraint")
    geometry: Union[Point, Polygon] = Field(description="Spatial geometry")
    srid: int = Field(default=4326, description="Spatial reference system ID")
    buffer: Optional[float] = Field(default=None, description="Buffer distance in meters")
    operation: str = Field(description="Spatial operation (within, intersects, distance)")
    
    class Config:
        arbitrary_types_allowed = True


class TemporalConstraint(BaseModel):
    """Temporal constraint definition."""
    start_time: Optional[datetime] = Field(default=None, description="Start time")
    end_time: Optional[datetime] = Field(default=None, description="End time")
    duration: Optional[float] = Field(default=None, description="Duration in hours")
    time_windows: Optional[List[Dict[str, datetime]]] = Field(default=None, description="Time windows")


class CapacityConstraint(BaseModel):
    """Capacity constraint definition."""
    resource_type: str = Field(description="Type of resource")
    capacity: float = Field(description="Maximum capacity")
    current_usage: float = Field(default=0.0, description="Current usage")
    unit: str = Field(description="Unit of measurement")


class MathematicalConstraint(BaseModel):
    """Mathematical constraint definition for OR-Tools."""
    expression: str = Field(description="Mathematical expression")
    operator: str = Field(description="Constraint operator (<=, >=, ==)")
    rhs: float = Field(description="Right-hand side value")
    variables: List[str] = Field(description="Variable names in constraint")


class Constraint(BaseModel):
    """Generic constraint definition."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Constraint ID")
    name: str = Field(description="Constraint name")
    type: ConstraintType = Field(description="Constraint type (hard/soft)")
    weight: float = Field(default=1.0, description="Constraint weight for soft constraints")
    priority: int = Field(default=1, description="Constraint priority")
    
    # Constraint content - one of these must be provided
    spatial_constraint: Optional[SpatialConstraint] = Field(default=None, description="Spatial constraint")
    temporal_constraint: Optional[TemporalConstraint] = Field(default=None, description="Temporal constraint")
    capacity_constraint: Optional[CapacityConstraint] = Field(default=None, description="Capacity constraint")
    mathematical_constraint: Optional[MathematicalConstraint] = Field(default=None, description="Mathematical constraint")
    
    @validator("weight")
    def validate_weight(cls, v: float) -> float:
        """Validate constraint weight."""
        if v < 0:
            raise ValueError("Constraint weight must be non-negative")
        return v
    
    @validator("priority")
    def validate_priority(cls, v: int) -> int:
        """Validate constraint priority."""
        if v < 1:
            raise ValueError("Constraint priority must be positive")
        return v


class Objective(BaseModel):
    """Optimization objective definition."""
    name: str = Field(description="Objective name")
    type: str = Field(description="Objective type (minimize/maximize)")
    function: str = Field(description="Objective function expression")
    weight: float = Field(default=1.0, description="Objective weight")
    variables: List[str] = Field(description="Variables in objective")


class OptimizationParameters(BaseModel):
    """Optimization algorithm parameters."""
    xgboost_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="XGBoost-specific parameters"
    )
    pygad_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="PyGAD-specific parameters"
    )
    ortools_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="OR-Tools-specific parameters"
    )
    constraint_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Constraint weight overrides"
    )
    max_iterations: int = Field(default=1000, description="Maximum optimization iterations")
    time_limit: int = Field(default=300, description="Optimization time limit in seconds")
    convergence_threshold: float = Field(default=0.001, description="Convergence threshold")


class OptimizationRequest(BaseModel):
    """Main optimization request model."""
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Request ID")
    name: str = Field(description="Optimization problem name")
    description: Optional[str] = Field(default=None, description="Problem description")
    
    # Problem definition
    variables: Dict[str, Dict[str, Any]] = Field(
        description="Variable definitions with bounds and types"
    )
    objectives: List[Objective] = Field(description="Optimization objectives")
    constraints: List[Constraint] = Field(description="Problem constraints")
    
    # Input data
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for optimization"
    )
    
    # Configuration
    parameters: OptimizationParameters = Field(
        default_factory=OptimizationParameters,
        description="Optimization parameters"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Request metadata"
    )
    
    @validator("objectives")
    def validate_objectives(cls, v: List[Objective]) -> List[Objective]:
        """Validate that at least one objective is provided."""
        if not v:
            raise ValueError("At least one objective must be provided")
        return v
    
    @validator("variables")
    def validate_variables(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate variable definitions."""
        if not v:
            raise ValueError("At least one variable must be defined")
        
        for var_name, var_def in v.items():
            if "type" not in var_def:
                raise ValueError(f"Variable '{var_name}' missing type definition")
            if "bounds" not in var_def and var_def["type"] in ["continuous", "integer"]:
                raise ValueError(f"Variable '{var_name}' missing bounds definition")
        
        return v


class Microtask(BaseModel):
    """Microtask definition for atomic operations."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Microtask ID")
    name: str = Field(description="Microtask name")
    task_type: str = Field(description="Task type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    status: MicrotaskStatus = Field(default=MicrotaskStatus.PENDING, description="Task status")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Task error message")
    execution_time: Optional[float] = Field(default=None, description="Execution time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")


class Solution(BaseModel):
    """Optimization solution representation."""
    solution_id: str = Field(default_factory=lambda: str(uuid4()), description="Solution ID")
    variables: Dict[str, Any] = Field(description="Variable values")
    objectives: Dict[str, float] = Field(description="Objective values")
    constraint_violations: Dict[str, float] = Field(
        default_factory=dict,
        description="Constraint violation scores"
    )
    fitness_score: float = Field(description="Overall fitness score")
    rank: int = Field(default=1, description="Solution rank (1 = best)")
    is_feasible: bool = Field(description="Whether solution satisfies all hard constraints")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Solution metadata")


class OptimizationResponse(BaseModel):
    """Optimization response model."""
    request_id: str = Field(description="Original request ID")
    status: OptimizationStatus = Field(description="Optimization status")
    
    # Results
    solutions: List[Solution] = Field(default_factory=list, description="Optimization solutions")
    best_solution: Optional[Solution] = Field(default=None, description="Best solution")
    
    # Execution details
    execution_time: float = Field(description="Total execution time in seconds")
    microtasks: List[Microtask] = Field(default_factory=list, description="Executed microtasks")
    
    # Metrics
    convergence_history: List[Dict[str, float]] = Field(
        default_factory=list,
        description="Convergence history"
    )
    constraint_satisfaction: Dict[str, float] = Field(
        default_factory=dict,
        description="Constraint satisfaction rates"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    
    # Error information
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information if failed")


class LogEntry(BaseModel):
    """Structured log entry model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")
    level: LogLevel = Field(description="Log level")
    message: str = Field(description="Log message")
    logger: str = Field(description="Logger name")
    request_id: Optional[str] = Field(default=None, description="Request ID")
    microtask_id: Optional[str] = Field(default=None, description="Microtask ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional log details")
    
    class Config:
        use_enum_values = True


class Metrics(BaseModel):
    """Performance metrics model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID")
    
    # Performance metrics
    response_time: Optional[float] = Field(default=None, description="Response time in seconds")
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(default=None, description="Memory usage in MB")
    
    # Application metrics
    active_requests: Optional[int] = Field(default=None, description="Number of active requests")
    queue_size: Optional[int] = Field(default=None, description="Queue size")
    error_rate: Optional[float] = Field(default=None, description="Error rate percentage")
    
    # Optimization metrics
    solutions_found: Optional[int] = Field(default=None, description="Number of solutions found")
    iterations_completed: Optional[int] = Field(default=None, description="Number of iterations")
    convergence_rate: Optional[float] = Field(default=None, description="Convergence rate")


# Type aliases for common use cases
VariableDict = Dict[str, Dict[str, Any]]
ConstraintDict = Dict[str, Constraint]
ObjectiveDict = Dict[str, Objective]
SolutionDict = Dict[str, Solution]