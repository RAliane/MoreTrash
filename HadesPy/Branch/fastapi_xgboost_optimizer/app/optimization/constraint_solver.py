"""
Constraint solver using Google OR-Tools CP-SAT.

This module implements constraint programming using Google's OR-Tools
CP-SAT solver for handling complex mathematical constraints.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from app.core.config import settings
from app.core.exceptions import ConstraintException, OptimizationException
from app.infrastructure.logging_config import get_logger


class ConstraintSolver:
    """
    Constraint solver using Google OR-Tools CP-SAT.
    
    Handles mathematical constraints, integer programming, and
    constraint satisfaction problems.
    """
    
    def __init__(self):
        """Initialize the constraint solver."""
        self.logger = get_logger(__name__)
        self.is_ready = False
        
        # Default solver parameters
        self.default_params = {
            "max_time_in_seconds": settings.ORTOOLS_MAX_TIME,
            "num_search_workers": settings.ORTOOLS_NUM_SEARCH_WORKERS,
            "enumerate_all_solutions": False,
            "log_search_progress": False,
        }
        
        self.logger.info("Constraint solver initialized")
    
    async def solve_constraint_problem(
        self,
        variables: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        objectives: Optional[List[Dict[str, Any]]] = None,
        solver_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Solve a constraint satisfaction/optimization problem.
        
        Args:
            variables: Variable definitions with bounds and types
            constraints: List of mathematical constraints
            objectives: List of optimization objectives
            solver_params: OR-Tools solver parameters
            
        Returns:
            Dict[str, Any]: Solution results
            
        Raises:
            ConstraintException: If problem is infeasible
            OptimizationException: If solving fails
        """
        try:
            start_time = time.time()
            
            # Create model
            model = cp_model.CpModel()
            
            # Create variables
            cp_variables = await self._create_cp_variables(model, variables)
            
            # Add constraints
            await self._add_constraints(model, cp_variables, constraints)
            
            # Add objectives if provided
            if objectives:
                await self._add_objectives(model, cp_variables, objectives)
            
            # Create solver
            solver = cp_model.CpSolver()
            
            # Set solver parameters
            params = {**self.default_params, **(solver_params or {})}
            for key, value in params.items():
                if hasattr(solver.parameters, key):
                    setattr(solver.parameters, key, value)
            
            # Solve
            self.logger.info(
                "Starting constraint solver",
                extra={
                    "num_variables": len(variables),
                    "num_constraints": len(constraints),
                    "has_objectives": objectives is not None,
                }
            )
            
            status = solver.Solve(model)
            
            # Process results
            if status == cp_model.OPTIMAL:
                solution = await self._extract_solution(solver, cp_variables, variables)
                
                self.logger.info(
                    "Optimal solution found",
                    extra={
                        "objective_value": solver.ObjectiveValue(),
                        "solve_time": solver.WallTime(),
                    }
                )
                
                return {
                    "status": "optimal",
                    "solution": solution,
                    "objective_value": solver.ObjectiveValue(),
                    "solve_time": solver.WallTime(),
                    "num_conflicts": solver.NumConflicts(),
                    "num_branches": solver.NumBranches(),
                }
            
            elif status == cp_model.FEASIBLE:
                solution = await self._extract_solution(solver, cp_variables, variables)
                
                self.logger.info(
                    "Feasible solution found",
                    extra={
                        "objective_value": solver.ObjectiveValue(),
                        "solve_time": solver.WallTime(),
                    }
                )
                
                return {
                    "status": "feasible",
                    "solution": solution,
                    "objective_value": solver.ObjectiveValue(),
                    "solve_time": solver.WallTime(),
                }
            
            elif status == cp_model.INFEASIBLE:
                self.logger.warning("Problem is infeasible")
                raise ConstraintException(
                    message="Constraint problem is infeasible",
                    code="INFEASIBLE_CONSTRAINTS",
                    constraint_details={"num_constraints": len(constraints)},
                )
            
            else:
                self.logger.warning(f"Solver returned status: {status}")
                raise OptimizationException(
                    message=f"Solver failed with status: {status}",
                    code="SOLVER_FAILED",
                )
            
        except Exception as exc:
            if isinstance(exc, (ConstraintException, OptimizationException)):
                raise
            
            self.logger.error(
                "Constraint solving failed",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise OptimizationException(
                message="Constraint solving failed",
                code="CONSTRAINT_SOLVING_FAILED",
                engine_error=str(exc),
            )
    
    async def check_feasibility(
        self,
        constraints: List[Dict[str, Any]],
        variables: Dict[str, Any],
        timeout: int = 30,
    ) -> bool:
        """
        Check if constraints are feasible.
        
        Args:
            constraints: List of mathematical constraints
            variables: Variable definitions
            timeout: Maximum solving time
            
        Returns:
            bool: True if constraints are feasible, False otherwise
        """
        try:
            # Create minimal model for feasibility checking
            model = cp_model.CpModel()
            
            # Create variables
            cp_variables = await self._create_cp_variables(model, variables)
            
            # Add constraints
            await self._add_constraints(model, cp_variables, constraints)
            
            # Create solver with timeout
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = timeout
            solver.parameters.log_search_progress = False
            
            # Check feasibility
            status = solver.Solve(model)
            
            return status in [cp_model.FEASIBLE, cp_model.OPTIMAL]
            
        except Exception as exc:
            self.logger.error(
                "Feasibility check failed",
                extra={"error": str(exc)}
            )
            return False
    
    async def find_all_solutions(
        self,
        variables: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        max_solutions: int = 100,
        solver_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find all feasible solutions to a constraint problem.
        
        Args:
            variables: Variable definitions
            constraints: List of constraints
            max_solutions: Maximum number of solutions to find
            solver_params: Solver parameters
            
        Returns:
            List[Dict[str, Any]]: List of solutions
        """
        try:
            # Create model
            model = cp_model.CpModel()
            
            # Create variables
            cp_variables = await self._create_cp_variables(model, variables)
            
            # Add constraints
            await self._add_constraints(model, cp_variables, constraints)
            
            # Create solution collector
            class SolutionCollector(cp_model.CpSolverSolutionCallback):
                """Collect all solutions."""
                
                def __init__(self, variables):
                    super().__init__()
                    self.variables = variables
                    self.solutions = []
                    self.max_solutions = max_solutions
                
                def on_solution_callback(self):
                    if len(self.solutions) < self.max_solutions:
                        solution = {}
                        for var_name, var in self.variables.items():
                            solution[var_name] = self.Value(var)
                        self.solutions.append(solution)
                    
                    if len(self.solutions) >= self.max_solutions:
                        self.StopSearch()
            
            collector = SolutionCollector(cp_variables)
            
            # Create solver
            solver = cp_model.CpSolver()
            params = {**self.default_params, **(solver_params or {})}
            params["enumerate_all_solutions"] = True
            
            for key, value in params.items():
                if hasattr(solver.parameters, key):
                    setattr(solver.parameters, key, value)
            
            # Search for all solutions
            status = solver.SearchForAllSolutions(model, collector)
            
            if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
                self.logger.info(
                    f"Found {len(collector.solutions)} solutions",
                    extra={"num_solutions": len(collector.solutions)}
                )
                return collector.solutions
            else:
                self.logger.warning("No solutions found")
                return []
            
        except Exception as exc:
            self.logger.error(
                "Solution enumeration failed",
                extra={"error": str(exc)}
            )
            raise OptimizationException(
                message="Solution enumeration failed",
                code="SOLUTION_ENUMERATION_FAILED",
                engine_error=str(exc),
            )
    
    async def optimize_with_constraints(
        self,
        variables: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        objective: Dict[str, Any],
        solver_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Solve an optimization problem with constraints.
        
        Args:
            variables: Variable definitions
            constraints: List of constraints
            objective: Optimization objective
            solver_params: Solver parameters
            
        Returns:
            Dict[str, Any]: Optimization result
        """
        return await self.solve_constraint_problem(
            variables=variables,
            constraints=constraints,
            objectives=[objective],
            solver_params=solver_params,
        )
    
    async def _create_cp_variables(
        self, model: cp_model.CpModel, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create OR-Tools variables from definitions."""
        cp_variables = {}
        
        for var_name, var_def in variables.items():
            var_type = var_def["type"]
            
            if var_type == "continuous":
                # Convert to integer by scaling (CP-SAT only supports integers)
                bounds = var_def["bounds"]
                scale = var_def.get("scale", 100)  # Default scale factor
                
                cp_var = model.NewIntVar(
                    int(bounds[0] * scale),
                    int(bounds[1] * scale),
                    var_name,
                )
                cp_variables[var_name] = {"var": cp_var, "scale": scale}
            
            elif var_type == "integer":
                bounds = var_def["bounds"]
                cp_var = model.NewIntVar(
                    bounds[0], bounds[1], var_name
                )
                cp_variables[var_name] = {"var": cp_var}
            
            elif var_type == "binary":
                cp_var = model.NewBoolVar(var_name)
                cp_variables[var_name] = {"var": cp_var}
            
            else:
                raise ValueError(f"Unsupported variable type: {var_type}")
        
        return cp_variables
    
    async def _add_constraints(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        constraints: List[Dict[str, Any]],
    ) -> None:
        """Add constraints to the model."""
        for constraint in constraints:
            await self._add_constraint(model, cp_variables, constraint)
    
    async def _add_constraint(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        constraint: Dict[str, Any],
    ) -> None:
        """Add a single constraint to the model."""
        constraint_type = constraint.get("type", "linear")
        
        if constraint_type == "linear":
            await self._add_linear_constraint(model, cp_variables, constraint)
        elif constraint_type == "logical":
            await self._add_logical_constraint(model, cp_variables, constraint)
        else:
            raise ValueError(f"Unsupported constraint type: {constraint_type}")
    
    async def _add_linear_constraint(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        constraint: Dict[str, Any],
    ) -> None:
        """Add a linear constraint."""
        expression = constraint["expression"]
        operator = constraint["operator"]
        rhs = constraint["rhs"]
        
        # Build linear expression
        linear_expr = cp_model.LinearExpr()
        
        for var_name, coef in expression.items():
            if var_name in cp_variables:
                var_info = cp_variables[var_name]
                var = var_info["var"]
                scale = var_info.get("scale", 1)
                
                # Adjust coefficient for scaled variables
                adjusted_coef = coef / scale if scale != 1 else coef
                linear_expr += adjusted_coef * var
        
        # Add constraint based on operator
        if operator == "<=":
            model.Add(linear_expr <= rhs)
        elif operator == ">=":
            model.Add(linear_expr >= rhs)
        elif operator == "==":
            model.Add(linear_expr == rhs)
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    
    async def _add_logical_constraint(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        constraint: Dict[str, Any],
    ) -> None:
        """Add a logical constraint."""
        # Implementation for logical constraints
        # This would handle AND, OR, NOT, IMPLIES, etc.
        pass
    
    async def _add_objectives(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        objectives: List[Dict[str, Any]],
    ) -> None:
        """Add objectives to the model."""
        if len(objectives) == 1:
            # Single objective
            objective = objectives[0]
            await self._add_single_objective(model, cp_variables, objective)
        else:
            # Multi-objective (would need lexicographic or weighted approach)
            self.logger.warning(
                "Multiple objectives not fully supported, using first objective"
            )
            await self._add_single_objective(model, cp_variables, objectives[0])
    
    async def _add_single_objective(
        self,
        model: cp_model.CpModel,
        cp_variables: Dict[str, Any],
        objective: Dict[str, Any],
    ) -> None:
        """Add a single objective to the model."""
        objective_type = objective.get("type", "maximize")
        expression = objective.get("expression", {})
        
        # Build objective expression
        obj_expr = cp_model.LinearExpr()
        
        for var_name, coef in expression.items():
            if var_name in cp_variables:
                var_info = cp_variables[var_name]
                var = var_info["var"]
                scale = var_info.get("scale", 1)
                
                adjusted_coef = coef / scale if scale != 1 else coef
                obj_expr += adjusted_coef * var
        
        # Set objective
        if objective_type == "maximize":
            model.Maximize(obj_expr)
        elif objective_type == "minimize":
            model.Minimize(obj_expr)
        else:
            raise ValueError(f"Unsupported objective type: {objective_type}")
    
    async def _extract_solution(
        self,
        solver: cp_model.CpSolver,
        cp_variables: Dict[str, Any],
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract solution from solver."""
        solution = {}
        
        for var_name, var_info in cp_variables.items():
            cp_var = var_info["var"]
            scale = var_info.get("scale", 1)
            
            value = solver.Value(cp_var)
            
            # Scale back continuous variables
            if scale != 1:
                value = value / scale
            
            solution[var_name] = value
        
        return solution
    
    async def get_solver_statistics(self) -> Dict[str, Any]:
        """Get solver statistics and capabilities."""
        return {
            "solver": "Google OR-Tools CP-SAT",
            "version": "9.8.0",
            "capabilities": [
                "linear_constraints",
                "integer_programming",
                "boolean_constraints",
                "optimization",
                "solution_enumeration",
            ],
            "default_parameters": self.default_params,
        }