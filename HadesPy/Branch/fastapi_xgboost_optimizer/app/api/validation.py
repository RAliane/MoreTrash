"""
API validation models for the FastAPI XGBoost Optimizer.

This module defines Pydantic models for request/response validation
specific to the API layer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

from app.core.models import (
    Constraint,
    ConstraintType,
    Microtask,
    Objective,
    OptimizationParameters,
    OptimizationStatus,
    Solution,
    SpatialConstraint,
    TemporalConstraint,
    CapacityConstraint,
    MathematicalConstraint,
)


class OptimizationRequest(BaseModel):
    """API-level optimization request model."""
    name: str = Field(..., description="Optimization problem name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Problem description", max_length=1000)
    
    # Problem definition
    variables: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="Variable definitions with bounds and types",
        example={
            "x": {"type": "continuous", "bounds": [0, 100]},
            "y": {"type": "integer", "bounds": [0, 50]},
            "z": {"type": "binary"}
        }
    )
    
    objectives: List[Objective] = Field(
        ..., 
        description="Optimization objectives",
        min_items=1
    )
    
    constraints: List[Constraint] = Field(
        default_factory=list,
        description="Problem constraints"
    )
    
    # Input data
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for optimization"
    )
    
    # Configuration
    parameters: Optional[OptimizationParameters] = Field(
        None,
        description="Optimization parameters"
    )
    
    # Metadata
    tags: List[str] = Field(
        default_factory=list,
        description="Request tags for categorization"
    )
    priority: int = Field(
        default=1,
        description="Request priority (higher = more important)",
        ge=1,
        le=10
    )
    
    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate problem name."""
        if not v.strip():
            raise ValueError("Problem name cannot be empty")
        return v.strip()
    
    @validator("variables")
    def validate_variables(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate variable definitions."""
        if not v:
            raise ValueError("At least one variable must be defined")
        
        for var_name, var_def in v.items():
            if not isinstance(var_def, dict):
                raise ValueError(f"Variable '{var_name}' definition must be a dictionary")
            
            # Check required fields
            if "type" not in var_def:
                raise ValueError(f"Variable '{var_name}' must have a 'type' field")
            
            var_type = var_def["type"]
            valid_types = ["continuous", "integer", "binary", "categorical"]
            
            if var_type not in valid_types:
                raise ValueError(
                    f"Variable '{var_name}' has invalid type '{var_type}'. "
                    f"Must be one of: {valid_types}"
                )
            
            # Validate bounds for continuous and integer variables
            if var_type in ["continuous", "integer"]:
                if "bounds" not in var_def:
                    raise ValueError(f"Variable '{var_name}' of type '{var_type}' must have 'bounds'")
                
                bounds = var_def["bounds"]
                if not isinstance(bounds, list) or len(bounds) != 2:
                    raise ValueError(f"Variable '{var_name}' bounds must be a list of length 2")
                
                if bounds[0] >= bounds[1]:
                    raise ValueError(f"Variable '{var_name}' lower bound must be less than upper bound")
            
            # Validate categorical variables
            if var_type == "categorical":
                if "categories" not in var_def:
                    raise ValueError(f"Variable '{var_name}' of type 'categorical' must have 'categories'")
                
                categories = var_def["categories"]
                if not isinstance(categories, list) or len(categories) < 2:
                    raise ValueError(f"Variable '{var_name}' categories must be a list with at least 2 items")
        
        return v
    
    @validator("objectives")
    def validate_objectives(cls, v: List[Objective]) -> List[Objective]:
        """Validate objectives."""
        if not v:
            raise ValueError("At least one objective must be provided")
        
        # Check for duplicate objective names
        names = [obj.name for obj in v]
        if len(names) != len(set(names)):
            raise ValueError("Objective names must be unique")
        
        return v
    
    @validator("constraints")
    def validate_constraints(cls, v: List[Constraint]) -> List[Constraint]:
        """Validate constraints."""
        # Check for duplicate constraint names
        names = [constraint.name for constraint in v]
        if len(names) != len(set(names)):
            raise ValueError("Constraint names must be unique")
        
        return v


class BatchOptimizationRequest(BaseModel):
    """Batch optimization request model."""
    requests: List[OptimizationRequest] = Field(
        ..., 
        description="List of optimization requests",
        min_items=1,
        max_items=100  # Limit batch size
    )
    
    batch_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Batch processing configuration"
    )
    
    @validator("requests")
    def validate_requests(cls, v: List[OptimizationRequest]) -> List[OptimizationRequest]:
        """Validate batch requests."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 requests")
        
        return v


class OptimizationResponse(BaseModel):
    """API-level optimization response model."""
    request_id: str = Field(..., description="Original request ID")
    status: OptimizationStatus = Field(..., description="Optimization status")
    
    # Results
    solutions: List[Solution] = Field(
        default_factory=list,
        description="Optimization solutions"
    )
    
    best_solution: Optional[Solution] = Field(
        None,
        description="Best solution found"
    )
    
    # Execution details
    execution_time: float = Field(
        ..., 
        description="Total execution time in seconds",
        ge=0
    )
    
    stage_completion: Dict[str, float] = Field(
        default_factory=dict,
        description="Completion percentage for each workflow stage"
    )
    
    # Metrics
    convergence_history: List[Dict[str, float]] = Field(
        default_factory=list,
        description="Convergence history over time"
    )
    
    constraint_satisfaction: Dict[str, float] = Field(
        default_factory=dict,
        description="Constraint satisfaction rates by constraint type"
    )
    
    # Metadata
    created_at: datetime = Field(..., description="Response timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )
    
    # Error information
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error information if optimization failed"
    )
    
    @validator("execution_time")
    def validate_execution_time(cls, v: float) -> float:
        """Validate execution time."""
        if v < 0:
            raise ValueError("Execution time cannot be negative")
        return v


class OptimizationStatusResponse(BaseModel):
    """Optimization status response model."""
    request_id: str = Field(..., description="Request ID")
    status: OptimizationStatus = Field(..., description="Current status")
    
    progress: float = Field(
        default=0.0,
        description="Overall progress percentage (0-100)",
        ge=0,
        le=100
    )
    
    current_stage: Optional[str] = Field(
        None,
        description="Current workflow stage"
    )
    
    stage_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed stage information"
    )
    
    estimated_completion_time: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    
    created_at: datetime = Field(..., description="Request creation time")
    started_at: Optional[datetime] = Field(
        None,
        description="Processing start time"
    )
    last_updated: Optional[datetime] = Field(
        None,
        description="Last status update"
    )
    
    @validator("progress")
    def validate_progress(cls, v: float) -> float:
        """Validate progress percentage."""
        return max(0.0, min(100.0, v))


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime: Optional[float] = Field(
        None,
        description="Service uptime in seconds"
    )
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Health status of individual services"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health details"
    )


class MetricsResponse(BaseModel):
    """Metrics response model."""
    timestamp: float = Field(..., description="Metrics timestamp")
    uptime: Optional[float] = Field(
        None,
        description="Service uptime in seconds"
    )
    
    # Request metrics
    requests_total: int = Field(
        default=0,
        description="Total number of requests"
    )
    requests_per_minute: float = Field(
        default=0.0,
        description="Requests per minute"
    )
    average_response_time: float = Field(
        default=0.0,
        description="Average response time in seconds"
    )
    error_rate: float = Field(
        default=0.0,
        description="Error rate percentage"
    )
    
    # Optimization metrics
    active_optimizations: int = Field(
        default=0,
        description="Number of active optimizations"
    )
    completed_optimizations: int = Field(
        default=0,
        description="Number of completed optimizations"
    )
    failed_optimizations: int = Field(
        default=0,
        description="Number of failed optimizations"
    )
    
    # Quality metrics
    constraint_satisfaction_rate: float = Field(
        default=0.0,
        description="Average constraint satisfaction rate"
    )
    average_fitness_score: float = Field(
        default=0.0,
        description="Average fitness score"
    )
    
    # Resource metrics
    cpu_usage: Optional[float] = Field(
        None,
        description="CPU usage percentage"
    )
    memory_usage: Optional[float] = Field(
        None,
        description="Memory usage in MB"
    )
    
    @validator("error_rate", "constraint_satisfaction_rate")
    def validate_percentage(cls, v: float) -> float:
        """Validate percentage values."""
        return max(0.0, min(100.0, v))


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(
        None,
        description="Request ID (if applicable)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": {
                        "cause": "Invalid value for field 'objectives'",
                        "context": "OptimizationRequest validation",
                        "suggestion": "Check that objectives list is not empty",
                        "field": "objectives",
                        "value": []
                    }
                },
                "timestamp": "2026-01-12T10:30:00Z",
                "request_id": "req-1234567890"
            }
        }


class ConstraintExamples(BaseModel):
    """Examples of different constraint types."""
    spatial_constraint: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "distance",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "srid": 4326,
            "operation": "within",
            "buffer": 1000.0
        },
        description="Spatial constraint example"
    )
    
    temporal_constraint: Dict[str, Any] = Field(
        default_factory=lambda: {
            "start_time": "2026-01-12T09:00:00Z",
            "end_time": "2026-01-12T17:00:00Z",
            "duration": 8.0
        },
        description="Temporal constraint example"
    )
    
    capacity_constraint: Dict[str, Any] = Field(
        default_factory=lambda: {
            "resource_type": "truck",
            "capacity": 1000.0,
            "current_usage": 250.0,
            "unit": "kg"
        },
        description="Capacity constraint example"
    )
    
    mathematical_constraint: Dict[str, Any] = Field(
        default_factory=lambda: {
            "expression": "2*x + 3*y",
            "operator": "<=",
            "rhs": 100.0,
            "variables": ["x", "y"]
        },
        description="Mathematical constraint example"
    )


class OptimizationExamples(BaseModel):
    """Example optimization requests for documentation."""
    simple_optimization: Dict[str, Any] = Field(
        default_factory=lambda: {
            "name": "Simple Linear Optimization",
            "description": "Maximize profit with resource constraints",
            "variables": {
                "x": {"type": "continuous", "bounds": [0, 100]},
                "y": {"type": "continuous", "bounds": [0, 50]}
            },
            "objectives": [
                {
                    "name": "profit",
                    "type": "maximize",
                    "function": "3*x + 2*y",
                    "weight": 1.0,
                    "variables": ["x", "y"]
                }
            ],
            "constraints": [
                {
                    "name": "resource_limit",
                    "type": "hard",
                    "weight": 1.0,
                    "priority": 1,
                    "mathematical_constraint": {
                        "expression": "2*x + y",
                        "operator": "<=",
                        "rhs": 150.0,
                        "variables": ["x", "y"]
                    }
                }
            ]
        },
        description="Simple optimization example"
    )
    
    spatial_optimization: Dict[str, Any] = Field(
        default_factory=lambda: {
            "name": "Facility Location Optimization",
            "description": "Find optimal facility locations with distance constraints",
            "variables": {
                "facility_x": {"type": "continuous", "bounds": [0, 1000]},
                "facility_y": {"type": "continuous", "bounds": [0, 1000]}
            },
            "objectives": [
                {
                    "name": "minimize_distance",
                    "type": "minimize",
                    "function": "sqrt((facility_x - 500)^2 + (facility_y - 500)^2)",
                    "weight": 1.0,
                    "variables": ["facility_x", "facility_y"]
                }
            ],
            "constraints": [
                {
                    "name": "distance_to_customers",
                    "type": "soft",
                    "weight": 0.8,
                    "priority": 2,
                    "spatial_constraint": {
                        "type": "distance",
                        "geometry": {"type": "Point", "coordinates": [500, 500]},
                        "srid": 3857,
                        "operation": "within",
                        "buffer": 200.0
                    }
                }
            ]
        },
        description="Spatial optimization example"
    )