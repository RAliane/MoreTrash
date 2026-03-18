"""
Test configuration and fixtures for FastAPI XGBoost Optimizer.

This module provides pytest fixtures and configuration for testing.
"""

import asyncio
from typing import Any, Dict, Generator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import create_app


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Create a test application."""
    # Override settings for testing
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"
    settings.DATABASE_URL = TEST_DATABASE_URL
    
    app = create_app()
    return app


@pytest.fixture(scope="session")
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def sync_client(test_app: FastAPI) -> TestClient:
    """Create a synchronous test client."""
    return TestClient(test_app)


@pytest.fixture(scope="function")
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with SessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_xgboost_engine() -> MagicMock:
    """Mock XGBoost engine."""
    mock = MagicMock()
    mock.predict.return_value = {
        "score": 0.85,
        "constraint_satisfaction": 0.92,
        "overall_score": 0.88,
    }
    mock.is_ready = True
    return mock


@pytest.fixture
def mock_genetic_optimizer() -> MagicMock:
    """Mock genetic optimizer."""
    mock = MagicMock()
    mock.optimize.return_value = [
        {
            "variables": {"x": 10, "y": 20},
            "objectives": {"profit": 100},
            "fitness": 0.95,
            "feasible": True,
            "metadata": {"generation": 25},
        }
    ]
    return mock


@pytest.fixture
def mock_constraint_solver() -> MagicMock:
    """Mock constraint solver."""
    mock = MagicMock()
    mock.check_feasibility.return_value = True
    mock.solve_constraint_problem.return_value = {
        "status": "optimal",
        "solution": {"x": 10, "y": 20},
        "objective_value": 100,
        "solve_time": 0.5,
    }
    return mock


@pytest.fixture
def mock_knn_service() -> MagicMock:
    """Mock KNN service."""
    mock = MagicMock()
    mock.find_nearest_neighbors.return_value = [
        {"id": 1, "distance": 100.5},
        {"id": 2, "distance": 150.2},
    ]
    mock.check_constraint_violations.return_value = []
    return mock


@pytest.fixture
def sample_optimization_request() -> Dict[str, Any]:
    """Sample optimization request data."""
    return {
        "name": "Test Optimization",
        "description": "Test optimization problem",
        "variables": {
            "x": {"type": "continuous", "bounds": [0, 100]},
            "y": {"type": "continuous", "bounds": [0, 50]},
        },
        "objectives": [
            {
                "name": "profit",
                "type": "maximize",
                "function": "3*x + 2*y",
                "weight": 1.0,
                "variables": ["x", "y"],
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
                    "variables": ["x", "y"],
                },
            }
        ],
        "parameters": {
            "max_iterations": 1000,
            "time_limit": 300,
        },
    }


@pytest.fixture
def sample_optimization_response() -> Dict[str, Any]:
    """Sample optimization response data."""
    return {
        "request_id": "test-request-123",
        "status": "completed",
        "solutions": [
            {
                "solution_id": "sol-1",
                "variables": {"x": 25, "y": 50},
                "objectives": {"profit": 175},
                "fitness_score": 0.95,
                "rank": 1,
                "is_feasible": True,
                "metadata": {"generation": 25},
            }
        ],
        "best_solution": {
            "solution_id": "sol-1",
            "variables": {"x": 25, "y": 50},
            "objectives": {"profit": 175},
            "fitness_score": 0.95,
            "rank": 1,
            "is_feasible": True,
            "metadata": {"generation": 25},
        },
        "execution_time": 2.5,
        "stage_completion": {
            "input_validation": 100.0,
            "constraint_validation": 100.0,
            "optimization": 100.0,
        },
        "convergence_history": [
            {"generation": 1, "fitness": 0.5},
            {"generation": 10, "fitness": 0.8},
            {"generation": 25, "fitness": 0.95},
        ],
        "constraint_satisfaction": {
            "resource_limit": 1.0,
        },
        "created_at": "2026-01-12T10:30:00Z",
        "metadata": {
            "num_solutions": 1,
            "validation_rate": 1.0,
        },
    }


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Authentication headers for testing."""
    return {
        "Authorization": "Bearer test-api-key",
        "X-API-Key": "test-api-key",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Override any global settings for tests
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"
    settings.RATE_LIMIT = "1000/minute"  # Higher limit for tests
    
    yield
    
    # Cleanup after tests
    pass


@pytest.fixture
def mock_spatial_constraint():
    """Mock spatial constraint."""
    from shapely.geometry import Point
    
    return {
        "type": "distance",
        "geometry": Point(0, 0),
        "srid": 4326,
        "operation": "within",
        "buffer": 1000.0,
    }


@pytest.fixture
def mock_temporal_constraint():
    """Mock temporal constraint."""
    from datetime import datetime
    
    return {
        "start_time": datetime(2026, 1, 12, 9, 0, 0),
        "end_time": datetime(2026, 1, 12, 17, 0, 0),
        "duration": 8.0,
    }


@pytest.fixture
def mock_capacity_constraint():
    """Mock capacity constraint."""
    return {
        "resource_type": "truck",
        "capacity": 1000.0,
        "current_usage": 250.0,
        "unit": "kg",
    }


@pytest.fixture
def mock_mathematical_constraint():
    """Mock mathematical constraint."""
    return {
        "expression": "2*x + 3*y",
        "operator": "<=",
        "rhs": 100.0,
        "variables": ["x", "y"],
    }