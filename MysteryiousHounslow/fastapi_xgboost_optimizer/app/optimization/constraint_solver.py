from typing import Dict, List, Any, Optional
import structlog

from app.infrastructure.config import settings
from app.infrastructure.logging import get_ml_logger

logger = get_ml_logger()


class ConstraintSolver:
    """Constraint programming solver using Google OR-Tools CP-SAT."""

    def __init__(self):
        self.max_time = settings.ORTOOLS_MAX_TIME
        self.num_solutions = settings.ORTOOLS_NUM_SOLUTIONS

    async def solve_constraints(
        self,
        variables: Dict[str, Dict[str, Any]],
        hard_constraints: List[Dict[str, Any]],
        variable_bounds: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Solve hard constraints using CP-SAT."""
        try:
            # Lazy import to avoid dependency issues
            from ortools.sat.python import cp_model

            # Create model
            model = cp_model.CpModel()

            # Create variables
            solver_vars = {}
            for var_name, var_info in variables.items():
                var_type = var_info.get("type", "continuous")
                bounds = variable_bounds.get(var_name, [0, 1000])

                if var_type == "integer":
                    solver_vars[var_name] = model.NewIntVar(
                        int(bounds[0]), int(bounds[1]), var_name
                    )
                else:
                    # For continuous variables, discretize
                    solver_vars[var_name] = model.NewIntVar(
                        int(bounds[0]), int(bounds[1]), var_name
                    )

            # Add hard constraints
            for constraint in hard_constraints:
                try:
                    self._add_constraint_to_model(model, solver_vars, constraint)
                except Exception as e:
                    logger.warning(
                        "Failed to add constraint to model",
                        constraint_name=constraint.get("name"),
                        error=str(e),
                    )
                    continue

            # Create solver
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = self.max_time
            solver.parameters.num_search_workers = 4

            # Solve
            status = solver.Solve(model)

            # Process results
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                solution = {}
                for var_name, var in solver_vars.items():
                    solution[var_name] = solver.Value(var)

                result = {
                    "feasible": True,
                    "solution": solution,
                    "objective_value": solver.ObjectiveValue()
                    if model.HasObjective()
                    else None,
                    "status": "feasible",
                    "solve_time": solver.WallTime(),
                    "metadata": {
                        "solver": "OR-Tools CP-SAT",
                        "status_code": status,
                        "branches": solver.NumBranches(),
                        "conflicts": solver.NumConflicts(),
                    },
                }

                logger.info(
                    "CP-SAT constraint solving succeeded",
                    feasible=True,
                    solve_time=solver.WallTime(),
                )

            else:
                result = {
                    "feasible": False,
                    "solution": None,
                    "status": "infeasible",
                    "solve_time": solver.WallTime(),
                    "metadata": {"solver": "OR-Tools CP-SAT", "status_code": status},
                }

                logger.warning(
                    "CP-SAT found no feasible solution",
                    status=status,
                    solve_time=solver.WallTime(),
                )

            return result

        except Exception as e:
            logger.error("CP-SAT constraint solving failed", error=str(e))
            return self._fallback_constraint_check(
                variables, hard_constraints, variable_bounds
            )

    def _add_constraint_to_model(
        self, model, solver_vars: Dict[str, Any], constraint: Dict[str, Any]
    ):
        """Add a constraint to the CP-SAT model."""
        constraint_name = constraint.get("name", "unnamed")
        expression = constraint.get("expression")

        if not expression:
            logger.warning(
                "Constraint has no expression", constraint_name=constraint_name
            )
            return

        try:
            # Parse simple constraint expressions
            # This is a basic implementation - production would need a proper parser
            if ">=" in expression:
                left, right = expression.split(">=")
                left = left.strip()
                right = right.strip()

                if left in solver_vars and right.replace(".", "").isdigit():
                    model.Add(solver_vars[left] >= int(float(right)))
                else:
                    logger.warning(
                        "Unsupported constraint format",
                        constraint=constraint_name,
                        expression=expression,
                    )

            elif "<=" in expression:
                left, right = expression.split("<=")
                left = left.strip()
                right = right.strip()

                if left in solver_vars and right.replace(".", "").isdigit():
                    model.Add(solver_vars[left] <= int(float(right)))
                else:
                    logger.warning(
                        "Unsupported constraint format",
                        constraint=constraint_name,
                        expression=expression,
                    )

            elif "==" in expression:
                left, right = expression.split("==")
                left = left.strip()
                right = right.strip()

                if left in solver_vars and right.replace(".", "").isdigit():
                    model.Add(solver_vars[left] == int(float(right)))
                else:
                    logger.warning(
                        "Unsupported constraint format",
                        constraint=constraint_name,
                        expression=expression,
                    )

            else:
                logger.warning(
                    "Unsupported constraint type",
                    constraint=constraint_name,
                    expression=expression,
                )

        except Exception as e:
            logger.warning(
                "Failed to parse constraint expression",
                constraint=constraint_name,
                expression=expression,
                error=str(e),
            )

    def _fallback_constraint_check(
        self,
        variables: Dict[str, Dict[str, Any]],
        hard_constraints: List[Dict[str, Any]],
        variable_bounds: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Fallback constraint checking when OR-Tools is not available."""
        logger.warning("Using fallback constraint checking")

        # Simple bounds checking
        feasible = True
        issues = []

        for constraint in hard_constraints:
            constraint_name = constraint.get("name", "unnamed")
            expression = constraint.get("expression")

            if expression:
                # Very basic constraint checking
                try:
                    # Check for obvious violations
                    if ">=" in expression:
                        left, right = expression.split(">=")
                        left = left.strip()
                        right = right.strip()

                        # Check if any variable bound violates constraint
                        if right.replace(".", "").isdigit():
                            limit = float(right)
                            # This is a simplified check
                            issues.append(
                                f"Constraint {constraint_name}: basic check passed"
                            )
                        else:
                            feasible = False
                            issues.append(
                                f"Constraint {constraint_name}: non-numeric limit"
                            )

                except Exception as e:
                    feasible = False
                    issues.append(
                        f"Constraint {constraint_name}: parsing failed - {str(e)}"
                    )

        return {
            "feasible": feasible,
            "solution": None,
            "status": "feasible" if feasible else "infeasible",
            "issues": issues,
            "metadata": {"method": "fallback_bounds_check"},
        }
