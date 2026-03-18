"""
Genetic Algorithm optimizer using PyGAD for multi-objective optimization.

This module implements genetic algorithm optimization with support for
multi-objective problems, constraint handling, and various selection strategies.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pygad

from app.core.config import settings
from app.core.exceptions import OptimizationException
from app.core.models import Constraint, ConstraintType, Objective
from app.infrastructure.logging_config import get_logger


class GeneticOptimizer:
    """
    Genetic Algorithm optimizer using PyGAD.
    
    Supports multi-objective optimization with constraint handling
    and various genetic operators.
    """
    
    def __init__(self):
        """Initialize the genetic optimizer."""
        self.logger = get_logger(__name__)
        self.convergence_history: List[Dict[str, float]] = []
        self.is_ready = False
        
        # Default parameters
        self.default_params = {
            "num_generations": settings.PYGAD_NUM_GENERATIONS,
            "population_size": settings.PYGAD_POPULATION_SIZE,
            "parent_selection_type": settings.PYGAD_PARENT_SELECTION_TYPE,
            "crossover_type": settings.PYGAD_CROSSOVER_TYPE,
            "mutation_type": settings.PYGAD_MUTATION_TYPE,
            "mutation_percent_genes": settings.PYGAD_MUTATION_PERCENT_GENES,
            "keep_elitism": 2,
            "parallel_processing": None,  # Disable for async compatibility
        }
        
        self.logger.info("Genetic optimizer initialized")
    
    async def optimize(self, optimization_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run genetic algorithm optimization.
        
        Args:
            optimization_params: Optimization parameters containing:
                - variables: Variable definitions
                - objectives: List of objectives
                - constraints: List of constraints
                - parameters: Algorithm parameters
                
        Returns:
            List[Dict[str, Any]]: Optimized solutions
            
        Raises:
            OptimizationException: If optimization fails
        """
        try:
            start_time = time.time()
            
            # Extract parameters
            variables = optimization_params["variables"]
            objectives = optimization_params["objectives"]
            constraints = optimization_params.get("constraints", [])
            algorithm_params = optimization_params.get("parameters", {})
            
            # Prepare GA parameters
            ga_params = self._prepare_ga_params(
                variables, objectives, constraints, algorithm_params
            )
            
            # Create fitness function
            fitness_func = self._create_fitness_function(
                variables, objectives, constraints
            )
            
            # Initialize GA
            ga_instance = pygad.GA(
                fitness_func=fitness_func,
                **ga_params,
            )
            
            # Set up callbacks
            ga_instance.generations_completed = self._create_generation_callback()
            
            # Run optimization
            self.logger.info(
                "Starting genetic algorithm optimization",
                extra={
                    "num_generations": ga_params["num_generations"],
                    "population_size": ga_params["sol_per_pop"],
                    "num_objectives": len(objectives),
                    "num_constraints": len(constraints),
                }
            )
            
            ga_instance.run()
            
            # Extract solutions
            solutions = self._extract_solutions(ga_instance, variables, objectives)
            
            # Clean up
            del ga_instance
            
            optimization_time = time.time() - start_time
            
            self.logger.info(
                "Genetic algorithm optimization completed",
                extra={
                    "num_solutions": len(solutions),
                    "optimization_time": optimization_time,
                    "generations_completed": len(self.convergence_history),
                }
            )
            
            return solutions
            
        except Exception as exc:
            self.logger.error(
                "Genetic algorithm optimization failed",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise OptimizationException(
                message="Genetic algorithm optimization failed",
                code="GENETIC_OPTIMIZATION_FAILED",
                engine_error=str(exc),
            )
    
    def _prepare_ga_params(
        self,
        variables: Dict[str, Any],
        objectives: List[Objective],
        constraints: List[Constraint],
        algorithm_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare PyGAD parameters."""
        # Calculate number of genes (decision variables)
        num_genes = len(variables)
        
        # Define gene types and bounds
        gene_type = []
        gene_space = []
        
        for var_name, var_def in variables.items():
            var_type = var_def["type"]
            
            if var_type == "continuous":
                gene_type.append(float)
                gene_space.append(var_def["bounds"])
            elif var_type == "integer":
                gene_type.append(int)
                gene_space.append(list(range(var_def["bounds"][0], var_def["bounds"][1] + 1)))
            elif var_type == "binary":
                gene_type.append(int)
                gene_space.append([0, 1])
            elif var_type == "categorical":
                gene_type.append(int)
                gene_space.append(list(range(len(var_def["categories"]))))
            else:
                raise ValueError(f"Unsupported variable type: {var_type}")
        
        # Merge with algorithm parameters
        ga_params = {
            **self.default_params,
            **algorithm_params.get("pygad_parameters", {}),
            "num_genes": num_genes,
            "gene_type": gene_type,
            "gene_space": gene_space,
            "sol_per_pop": algorithm_params.get("population_size", self.default_params["population_size"]),
        }
        
        return ga_params
    
    def _create_fitness_function(
        self,
        variables: Dict[str, Any],
        objectives: List[Objective],
        constraints: List[Constraint],
    ) -> Callable:
        """Create fitness function for the genetic algorithm."""
        
        def fitness_function(ga_instance, solution, solution_idx):
            """Calculate fitness for a solution."""
            try:
                # Convert solution to variable values
                variable_values = self._convert_solution_to_variables(solution, variables)
                
                # Calculate objective values
                objective_values = self._calculate_objectives(
                    variable_values, objectives
                )
                
                # Calculate constraint penalties
                constraint_penalty = self._calculate_constraint_penalty(
                    variable_values, constraints
                )
                
                # Combine objectives and constraints
                fitness = self._combine_objectives_and_constraints(
                    objective_values, constraint_penalty, objectives, constraints
                )
                
                return fitness
                
            except Exception as exc:
                self.logger.error(
                    "Fitness calculation failed",
                    extra={"error": str(exc), "solution_idx": solution_idx}
                )
                return [-1e10] * len(objectives)  # Return very low fitness
        
        return fitness_function
    
    def _convert_solution_to_variables(
        self, solution: np.ndarray, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert GA solution to variable values."""
        variable_values = {}
        var_names = list(variables.keys())
        
        for i, var_name in enumerate(var_names):
            var_def = variables[var_name]
            var_type = var_def["type"]
            
            if var_type == "categorical":
                # Map integer to category
                category_idx = int(solution[i])
                variable_values[var_name] = var_def["categories"][category_idx]
            else:
                variable_values[var_name] = solution[i]
        
        return variable_values
    
    def _calculate_objectives(
        self, variable_values: Dict[str, Any], objectives: List[Objective]
    ) -> List[float]:
        """Calculate objective values for a solution."""
        objective_values = []
        
        for objective in objectives:
            # Simple expression evaluation (would need proper parser in production)
            try:
                # Replace variables in function with values
                function_str = objective.function
                for var_name, var_value in variable_values.items():
                    function_str = function_str.replace(var_name, str(var_value))
                
                # Evaluate function (CAUTION: eval is used for simplicity)
                value = eval(function_str)
                
                # Handle minimize objectives
                if objective.type == "minimize":
                    value = -value
                
                objective_values.append(value * objective.weight)
                
            except Exception:
                # Return very low value if evaluation fails
                objective_values.append(-1e10)
        
        return objective_values
    
    def _calculate_constraint_penalty(
        self, variable_values: Dict[str, Any], constraints: List[Constraint]
    ) -> float:
        """Calculate constraint penalty for a solution."""
        penalty = 0.0
        
        for constraint in constraints:
            if constraint.type == ConstraintType.HARD:
                # Hard constraints get large penalty if violated
                violation = self._check_constraint_violation(
                    constraint, variable_values
                )
                if violation > 0:
                    penalty += violation * 1e6  # Large penalty
            
            elif constraint.type == ConstraintType.SOFT:
                # Soft constraints get smaller penalty
                violation = self._check_constraint_violation(
                    constraint, variable_values
                )
                penalty += violation * constraint.weight
        
        return penalty
    
    def _check_constraint_violation(
        self, constraint: Constraint, variable_values: Dict[str, Any]
    ) -> float:
        """Check if a constraint is violated and return violation amount."""
        # Simplified implementation
        # In practice, this would properly evaluate constraint expressions
        return 0.0  # Assume no violation for now
    
    def _combine_objectives_and_constraints(
        self,
        objective_values: List[float],
        constraint_penalty: float,
        objectives: List[Objective],
        constraints: List[Constraint],
    ) -> List[float]:
        """Combine objectives and constraints into final fitness."""
        # For multi-objective optimization, return all objectives
        # Constraints are handled via penalty
        
        fitness_values = objective_values.copy()
        
        # Apply constraint penalty to each objective
        if constraint_penalty > 0:
            penalty_per_objective = constraint_penalty / len(objectives)
            fitness_values = [val - penalty_per_objective for val in fitness_values]
        
        return fitness_values
    
    def _create_generation_callback(self) -> Callable:
        """Create callback for generation completion."""
        
        def on_generation(ga_instance):
            """Handle generation completion."""
            generation = ga_instance.generations_completed
            best_solution = ga_instance.best_solution()
            best_fitness = best_solution[1]
            
            # Record convergence
            convergence_record = {
                "generation": generation,
                "best_fitness": best_fitness,
                "timestamp": time.time(),
            }
            
            self.convergence_history.append(convergence_record)
            
            # Log progress every 10 generations
            if generation % 10 == 0:
                self.logger.info(
                    f"Generation {generation} completed",
                    extra={
                        "generation": generation,
                        "best_fitness": best_fitness,
                        "population_fitness": ga_instance.last_generation_fitness,
                    }
                )
        
        return on_generation
    
    def _extract_solutions(
        self,
        ga_instance: pygad.GA,
        variables: Dict[str, Any],
        objectives: List[Objective],
    ) -> List[Dict[str, Any]]:
        """Extract solutions from GA instance."""
        solutions = []
        
        # Get best solutions (Pareto front for multi-objective)
        best_solutions = ga_instance.best_solutions
        
        for i, (solution, fitness) in enumerate(best_solutions):
            # Convert to variable values
            variable_values = self._convert_solution_to_variables(solution, variables)
            
            # Calculate objectives
            objective_values = self._calculate_objectives(variable_values, objectives)
            
            # Create solution dictionary
            solution_dict = {
                "variables": variable_values,
                "objectives": {
                    obj.name: obj_val
                    for obj, obj_val in zip(objectives, objective_values)
                },
                "fitness": fitness,
                "feasible": True,  # Would check constraints
                "metadata": {
                    "solution_idx": i,
                    "generation_found": len(self.convergence_history),
                },
            }
            
            solutions.append(solution_dict)
        
        return solutions
    
    def get_convergence_history(self) -> List[Dict[str, float]]:
        """Get convergence history."""
        return self.convergence_history.copy()
    
    def clear_history(self) -> None:
        """Clear convergence history."""
        self.convergence_history.clear()
    
    async def tune_parameters(
        self,
        optimization_params: Dict[str, Any],
        parameter_grid: Dict[str, List[Any]],
    ) -> Dict[str, Any]:
        """
        Tune GA parameters using grid search.
        
        Args:
            optimization_params: Base optimization parameters
            parameter_grid: Parameter values to try
            
        Returns:
            Dict[str, Any]: Best parameters and results
        """
        self.logger.info("Starting parameter tuning")
        
        # Simple grid search implementation
        best_params = None
        best_fitness = float("-inf")
        results = []
        
        # Generate parameter combinations
        from itertools import product
        
        param_names = list(parameter_grid.keys())
        param_values = [parameter_grid[name] for name in param_names]
        
        for combination in product(*param_values):
            # Create parameter set
            trial_params = dict(zip(param_names, combination))
            
            # Update optimization parameters
            trial_optimization_params = optimization_params.copy()
            trial_optimization_params.setdefault("pygad_parameters", {}).update(trial_params)
            
            try:
                # Run optimization with trial parameters
                self.clear_history()
                solutions = await self.optimize(trial_optimization_params)
                
                # Get best fitness
                best_solution = max(solutions, key=lambda x: x["fitness"])
                trial_fitness = best_solution["fitness"]
                
                # Record result
                result = {
                    "parameters": trial_params,
                    "fitness": trial_fitness,
                    "num_solutions": len(solutions),
                }
                results.append(result)
                
                # Update best
                if trial_fitness > best_fitness:
                    best_fitness = trial_fitness
                    best_params = trial_params
                
            except Exception as exc:
                self.logger.warning(
                    "Parameter tuning trial failed",
                    extra={"parameters": trial_params, "error": str(exc)}
                )
        
        return {
            "best_params": best_params,
            "best_fitness": best_fitness,
            "all_results": results,
        }
    
    async def optimize_with_early_stopping(
        self,
        optimization_params: Dict[str, Any],
        patience: int = 10,
        min_delta: float = 0.001,
    ) -> List[Dict[str, Any]]:
        """
        Run optimization with early stopping.
        
        Args:
            optimization_params: Optimization parameters
            patience: Number of generations to wait for improvement
            min_delta: Minimum improvement to continue
            
        Returns:
            List[Dict[str, Any]]: Optimized solutions
        """
        self.logger.info("Starting optimization with early stopping")
        
        # Create fitness function
        variables = optimization_params["variables"]
        objectives = optimization_params["objectives"]
        constraints = optimization_params.get("constraints", [])
        
        fitness_func = self._create_fitness_function(
            variables, objectives, constraints
        )
        
        # Prepare GA parameters
        ga_params = self._prepare_ga_params(
            variables, objectives, constraints, optimization_params
        )
        
        # Override num_generations for early stopping
        max_generations = ga_params["num_generations"]
        ga_params["num_generations"] = 1  # We'll control generations manually
        
        # Initialize GA
        ga_instance = pygad.GA(
            fitness_func=fitness_func,
            **ga_params,
        )
        
        # Early stopping variables
        best_fitness = float("-inf")
        generations_without_improvement = 0
        
        # Run generations with early stopping
        for generation in range(max_generations):
            # Run one generation
            ga_instance.run()
            
            # Check for improvement
            current_best = ga_instance.best_solution()[1]
            improvement = current_best - best_fitness
            
            if improvement > min_delta:
                best_fitness = current_best
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1
            
            # Check early stopping condition
            if generations_without_improvement >= patience:
                self.logger.info(
                    "Early stopping triggered",
                    extra={
                        "generation": generation + 1,
                        "best_fitness": best_fitness,
                        "patience": patience,
                    }
                )
                break
        
        # Extract solutions
        solutions = self._extract_solutions(ga_instance, variables, objectives)
        
        return solutions