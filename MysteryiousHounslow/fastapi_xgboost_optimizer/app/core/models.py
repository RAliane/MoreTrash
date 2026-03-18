from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Variable:
    """Business domain model for optimization variables."""

    name: str
    type: str  # "continuous", "integer", "categorical"
    bounds: Optional[List[float]] = None
    categories: Optional[List[str]] = None
    default_value: Optional[Any] = None


@dataclass
class Objective:
    """Business domain model for optimization objectives."""

    name: str
    type: str  # "minimize", "maximize"
    function: str
    weight: float = 1.0
    variables: List[str] = None


@dataclass
class Constraint:
    """Business domain model for optimization constraints."""

    name: str
    type: str  # "hard", "soft"
    weight: Optional[float] = None
    priority: int = 1
    expression: Optional[str] = None
    spatial_constraint: Optional[Dict[str, Any]] = None


@dataclass
class OptimizationProblem:
    """Business domain model for complete optimization problem."""

    name: str
    description: Optional[str] = None
    variables: List[Variable] = None
    objectives: List[Objective] = None
    constraints: List[Constraint] = None
    parameters: Dict[str, Any] = None


@dataclass
class SolutionCandidate:
    """Business domain model for solution candidates."""

    solution_id: str
    variables: Dict[str, Any]
    objectives: Dict[str, float]
    fitness_score: float
    rank: int
    is_feasible: bool
    metadata: Dict[str, Any] = None


@dataclass
class OptimizationResult:
    """Business domain model for optimization results."""

    request_id: str
    status: str
    solutions: List[SolutionCandidate] = None
    best_solution: Optional[SolutionCandidate] = None
    execution_time: Optional[float] = None
    convergence_history: List[Dict[str, Any]] = None
    constraint_satisfaction: Dict[str, float] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
