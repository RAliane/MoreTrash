import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# Test imports
def test_imports():
    """Test that all modules can be imported."""
    try:
        from app.main import app
        from app.core.schemas import OptimizationRequest, OptimizationResponse
        from app.orchestration.workflow import OptimizationWorkflow
        from app.optimization.xgboost_engine import XGBoostEngine
        from app.optimization.genetic_optimizer import GeneticOptimizer
        from app.optimization.constraint_solver import ConstraintSolver
        from app.optimization.knn_service import KNNService
        from app.database.postgis_client import PostGISClient
        from app.database.hasura_client import HasuraClient
        from app.infrastructure.config import settings
        from app.infrastructure.logging import setup_logging

        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_app_creation():
    """Test that FastAPI app can be created."""
    from app.main import app

    assert app.title == "FastAPI XGBoost Optimizer"
    assert app.version == "1.0.0"


@patch("app.infrastructure.cache.RedisCache.get")
@patch("app.infrastructure.cache.RedisCache.set")
def test_workflow_creation(mock_cache_set, mock_cache_get):
    """Test optimization workflow creation."""
    from app.orchestration.workflow import OptimizationWorkflow

    workflow = OptimizationWorkflow("test-request-id")

    assert workflow.request_id == "test-request-id"
    assert workflow.stage_completion.input_validation == 0.0


def test_schemas():
    """Test Pydantic schemas."""
    from app.core.schemas import (
        OptimizationRequest,
        VariableDefinition,
        ObjectiveDefinition,
    )

    # Test variable definition
    var_def = VariableDefinition(type="continuous", bounds=[0, 100])
    assert var_def.type == "continuous"
    assert var_def.bounds == [0, 100]

    # Test objective definition
    obj_def = ObjectiveDefinition(
        name="minimize_cost",
        type="minimize",
        function="x + y",
        weight=1.0,
        variables=["x", "y"],
    )
    assert obj_def.name == "minimize_cost"
    assert obj_def.type == "minimize"

    # Test optimization request
    request = OptimizationRequest(
        name="Test Optimization",
        variables={
            "x": VariableDefinition(type="continuous", bounds=[0, 10]),
            "y": VariableDefinition(type="continuous", bounds=[0, 10]),
        },
        objectives=[obj_def],
    )
    assert request.name == "Test Optimization"
    assert len(request.variables) == 2
    assert len(request.objectives) == 1


def test_config():
    """Test configuration loading."""
    from app.infrastructure.config import settings

    assert hasattr(settings, "PROJECT_NAME")
    assert hasattr(settings, "DEBUG")
    assert hasattr(settings, "DATABASE_URL")


def test_constraint_processor():
    """Test constraint processing."""
    from app.core.constraints import ConstraintProcessor

    processor = ConstraintProcessor()

    # Test separating constraints
    constraints = [
        {"name": "hard_constraint", "type": "hard"},
        {"name": "soft_constraint", "type": "soft"},
    ]

    hard, soft = processor.separate_constraints(constraints)

    assert len(hard) == 1
    assert len(soft) == 1
    assert hard[0]["name"] == "hard_constraint"
    assert soft[0]["name"] == "soft_constraint"


def test_data_processor():
    """Test data processing."""
    from app.core.processors import DataProcessor

    processor = DataProcessor()

    # Test variable normalization
    variables = [
        {"name": "x", "type": "continuous", "bounds": [0, 100]},
        {"name": "y", "type": "continuous", "bounds": [10, 50]},
    ]

    # Mock variable objects
    from app.core.models import Variable

    var_objects = [
        Variable(name="x", type="continuous", bounds=[0, 100]),
        Variable(name="y", type="continuous", bounds=[10, 50]),
    ]

    normalization = processor.normalize_variables(
        var_objects, {"x": [0, 100], "y": [10, 50]}
    )

    assert "x" in normalization
    assert "y" in normalization
    assert normalization["x"]["original_bounds"] == [0, 100]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
