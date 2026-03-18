from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class OptimizationStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VariableDefinition(BaseModel):
    type: str = Field(
        ..., description="Variable type (continuous, integer, categorical)"
    )
    bounds: Optional[List[Union[int, float]]] = Field(
        None, description="Variable bounds [min, max]"
    )
    categories: Optional[List[str]] = Field(None, description="Categorical values")
    default: Optional[Any] = Field(None, description="Default value")


class ObjectiveDefinition(BaseModel):
    name: str = Field(..., description="Objective name")
    type: str = Field(..., description="Objective type (minimize, maximize)")
    function: str = Field(..., description="Objective function expression")
    weight: float = Field(1.0, description="Objective weight")
    variables: List[str] = Field(..., description="Variables used in objective")


class SpatialConstraint(BaseModel):
    type: str = Field(
        ..., description="Spatial constraint type (distance, within, contains)"
    )
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry")
    srid: int = Field(3857, description="Spatial reference system ID")
    operation: str = Field(..., description="Spatial operation")
    buffer: Optional[float] = Field(None, description="Buffer distance")


class ConstraintDefinition(BaseModel):
    name: str = Field(..., description="Constraint name")
    type: str = Field(..., description="Constraint type (hard, soft)")
    weight: Optional[float] = Field(
        1.0, description="Constraint weight (for soft constraints)"
    )
    priority: Optional[int] = Field(1, description="Constraint priority")
    expression: Optional[str] = Field(None, description="Constraint expression")
    spatial_constraint: Optional[SpatialConstraint] = Field(
        None, description="Spatial constraint"
    )


class OptimizationParameters(BaseModel):
    max_iterations: int = Field(1000, description="Maximum iterations")
    time_limit: int = Field(300, description="Time limit in seconds")
    convergence_threshold: float = Field(0.001, description="Convergence threshold")
    population_size: int = Field(100, description="Genetic algorithm population size")
    mutation_rate: float = Field(0.1, description="Mutation rate")


class OptimizationRequest(BaseModel):
    name: str = Field(..., description="Optimization request name")
    description: Optional[str] = Field(None, description="Request description")
    variables: Dict[str, VariableDefinition] = Field(
        ..., description="Variable definitions"
    )
    objectives: List[ObjectiveDefinition] = Field(
        ..., description="Objective definitions"
    )
    constraints: List[ConstraintDefinition] = Field(
        ..., description="Constraint definitions"
    )
    parameters: OptimizationParameters = Field(
        default_factory=OptimizationParameters, description="Optimization parameters"
    )


class Solution(BaseModel):
    solution_id: str = Field(..., description="Solution ID")
    variables: Dict[str, Any] = Field(..., description="Variable values")
    objectives: Dict[str, float] = Field(..., description="Objective values")
    fitness_score: float = Field(..., description="Overall fitness score")
    rank: int = Field(..., description="Solution rank")
    is_feasible: bool = Field(..., description="Feasibility status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ConvergenceHistory(BaseModel):
    generation: int = Field(..., description="Generation number")
    fitness: float = Field(..., description="Best fitness score")


class StageCompletion(BaseModel):
    input_validation: float = Field(..., description="Input validation completion %")
    constraint_validation: float = Field(
        ..., description="Constraint validation completion %"
    )
    hard_constraint_enforcement: float = Field(
        ..., description="Hard constraint enforcement completion %"
    )
    soft_constraint_scoring: float = Field(
        ..., description="Soft constraint scoring completion %"
    )
    ml_scoring: float = Field(..., description="ML scoring completion %")
    optimization: float = Field(..., description="Optimization completion %")
    solution_validation: float = Field(
        ..., description="Solution validation completion %"
    )
    result_aggregation: float = Field(
        ..., description="Result aggregation completion %"
    )


class OptimizationResponse(BaseModel):
    request_id: str = Field(..., description="Request ID")
    status: str = Field(..., description="Request status")
    solutions: Optional[List[Solution]] = Field(
        None, description="Optimization solutions"
    )
    best_solution: Optional[Solution] = Field(None, description="Best solution")
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )
    stage_completion: Optional[StageCompletion] = Field(
        None, description="Stage completion status"
    )
    convergence_history: Optional[List[ConvergenceHistory]] = Field(
        None, description="Convergence history"
    )
    constraint_satisfaction: Optional[Dict[str, float]] = Field(
        None, description="Constraint satisfaction scores"
    )
    created_at: datetime = Field(..., description="Request creation timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Request completion timestamp"
    )
    message: Optional[str] = Field(None, description="Status message")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BatchOptimizationRequest(BaseModel):
    requests: List[OptimizationRequest] = Field(
        ..., description="List of optimization requests"
    )


class BatchOptimizationResponse(BaseModel):
    batch_id: str = Field(..., description="Batch ID")
    request_ids: List[str] = Field(..., description="Individual request IDs")
    status: str = Field(..., description="Batch status")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    total_requests: int = Field(..., description="Total number of requests")


class OptimizationStatus(BaseModel):
    request_id: str = Field(..., description="Request ID")
    status: str = Field(..., description="Request status")
    progress: Optional[float] = Field(None, description="Progress percentage")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    estimated_time_remaining: Optional[int] = Field(
        None, description="Estimated time remaining in seconds"
    )
    created_at: datetime = Field(..., description="Request creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
