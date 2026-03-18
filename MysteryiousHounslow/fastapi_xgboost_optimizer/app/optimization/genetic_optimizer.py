from typing import Dict, List, Any, Optional, Callable
import numpy as np
import structlog

from app.infrastructure.config import settings
from app.infrastructure.logging import get_ml_logger

logger = get_ml_logger()


class GeneticOptimizer:
    """Genetic algorithm optimization using PyGAD."""

    def __init__(self):
        self.population_size = settings.PYGAD_POPULATION_SIZE
        self.num_generations = settings.PYGAD_NUM_GENERATIONS
        self.mutation_rate = settings.PYGAD_MUTATION_RATE
        self.crossover_rate = settings.PYGAD_CROSSOVER_RATE

    async def optimize(
        self,
        fitness_function: Callable,
        variable_bounds: Dict[str, List[float]],
        variable_types: Dict[str, str],
        num_solutions: int = 10,
    ) -> Dict[str, Any]:
        """Run genetic algorithm optimization."""
        try:
            # Lazy import to avoid dependency issues
            import pygad

            # Prepare variable information
            var_names = list(variable_bounds.keys())
            num_variables = len(var_names)

            # Create gene space (variable bounds)
            gene_space = []
            gene_type = []

            for var_name in var_names:
                bounds = variable_bounds[var_name]
                var_type = variable_types.get(var_name, "continuous")

                if var_type == "integer":
                    gene_space.append(
                        {"low": int(bounds[0]), "high": int(bounds[1]), "step": 1}
                    )
                    gene_type.append(int)
                elif var_type == "categorical":
                    # For categorical, we'll use indices
                    gene_space.append(
                        {
                            "low": 0,
                            "high": len(bounds) - 1,  # bounds contains categories
                            "step": 1,
                        }
                    )
                    gene_type.append(int)
                else:  # continuous
                    gene_space.append({"low": bounds[0], "high": bounds[1]})
                    gene_type.append(float)

            # Create fitness function wrapper
            def pygad_fitness(ga_instance, solution, solution_idx):
                # Convert solution array to variable dict
                var_dict = {}
                for i, var_name in enumerate(var_names):
                    value = solution[i]
                    var_type = variable_types.get(var_name, "continuous")

                    if var_type == "categorical":
                        # Convert index back to category
                        categories = variable_bounds[var_name]
                        var_dict[var_name] = categories[int(value)]
                    else:
                        var_dict[var_name] = value

                return fitness_function(var_dict)

            # Create GA instance
            ga_instance = pygad.GA(
                num_generations=self.num_generations,
                num_parents_mating=int(self.population_size * 0.5),
                fitness_func=pygad_fitness,
                sol_per_pop=self.population_size,
                num_genes=num_variables,
                gene_space=gene_space,
                gene_type=gene_type,
                parent_selection_type="tournament",
                crossover_type="single_point",
                crossover_probability=self.crossover_rate,
                mutation_type="random",
                mutation_probability=self.mutation_rate,
                keep_parents=2,
                save_best_solutions=True,
                random_seed=42,
            )

            # Run optimization
            ga_instance.run()

            # Extract results
            best_solution, best_fitness, best_idx = ga_instance.best_solution()
            convergence_history = []

            # Build convergence history
            for gen in range(len(ga_instance.best_solutions_fitness)):
                convergence_history.append(
                    {
                        "generation": gen + 1,
                        "fitness": float(ga_instance.best_solutions_fitness[gen]),
                    }
                )

            # Get top solutions
            solutions = []
            fitness_values = ga_instance.last_generation_fitness

            # Sort by fitness (descending for maximization)
            sorted_indices = np.argsort(fitness_values)[::-1]

            for i in range(min(num_solutions, len(sorted_indices))):
                idx = sorted_indices[i]
                solution = ga_instance.population[idx]
                fitness = fitness_values[idx]

                # Convert to variable dict
                var_dict = {}
                for j, var_name in enumerate(var_names):
                    value = solution[j]
                    var_type = variable_types.get(var_name, "continuous")

                    if var_type == "categorical":
                        categories = variable_bounds[var_name]
                        var_dict[var_name] = categories[int(value)]
                    else:
                        var_dict[var_name] = value

                solutions.append(
                    {
                        "solution_id": f"sol-{i + 1}",
                        "variables": var_dict,
                        "fitness_score": float(fitness),
                        "rank": i + 1,
                        "is_feasible": True,  # Assume feasible for now
                        "metadata": {"generation": ga_instance.generations_completed},
                    }
                )

            result = {
                "solutions": solutions,
                "best_solution": solutions[0] if solutions else None,
                "convergence_history": convergence_history,
                "total_generations": ga_instance.generations_completed,
                "final_fitness": float(best_fitness),
                "metadata": {
                    "algorithm": "PyGAD",
                    "population_size": self.population_size,
                    "generations": ga_instance.generations_completed,
                },
            }

            logger.info(
                "Genetic optimization completed",
                generations=ga_instance.generations_completed,
                best_fitness=float(best_fitness),
                solutions_found=len(solutions),
            )

            return result

        except Exception as e:
            logger.error("Genetic optimization failed", error=str(e))
            return self._fallback_optimization(
                fitness_function, variable_bounds, variable_types, num_solutions
            )

    def _fallback_optimization(
        self,
        fitness_function: Callable,
        variable_bounds: Dict[str, List[float]],
        variable_types: Dict[str, str],
        num_solutions: int,
    ) -> Dict[str, Any]:
        """Fallback optimization when PyGAD is not available."""
        logger.warning("Using fallback optimization (random search)")

        solutions = []
        var_names = list(variable_bounds.keys())

        # Generate random solutions
        for i in range(num_solutions):
            var_dict = {}

            for var_name in var_names:
                bounds = variable_bounds[var_name]
                var_type = variable_types.get(var_name, "continuous")

                if var_type == "categorical":
                    # Random category selection
                    var_dict[var_name] = np.random.choice(bounds)
                else:
                    # Random value within bounds
                    var_dict[var_name] = np.random.uniform(bounds[0], bounds[1])

            fitness = fitness_function(var_dict)

            solutions.append(
                {
                    "solution_id": f"sol-{i + 1}",
                    "variables": var_dict,
                    "fitness_score": float(fitness),
                    "rank": i + 1,
                    "is_feasible": True,
                    "metadata": {"method": "random_search"},
                }
            )

        # Sort by fitness
        solutions.sort(key=lambda x: x["fitness_score"], reverse=True)

        return {
            "solutions": solutions,
            "best_solution": solutions[0] if solutions else None,
            "convergence_history": [],
            "metadata": {"method": "fallback_random_search"},
        }
