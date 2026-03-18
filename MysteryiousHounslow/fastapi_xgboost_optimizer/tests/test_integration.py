import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_optimization_endpoint_validation():
    """Test optimization endpoint input validation."""
    from app.main import app

    # Mock dependencies
    with (
        patch("app.api.endpoints.optimize.validate_api_key", return_value="test-key"),
        patch(
            "app.api.endpoints.optimize.get_current_user",
            return_value={"user_id": "test"},
        ),
        patch("app.orchestration.workflow.OptimizationWorkflow") as mock_workflow_class,
    ):
        mock_workflow = MagicMock()
        mock_workflow.process_request = AsyncMock()
        mock_workflow_class.return_value = mock_workflow

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            # Test valid request
            request_data = {
                "name": "Test Optimization",
                "variables": {
                    "x": {"type": "continuous", "bounds": [0, 10]},
                    "y": {"type": "continuous", "bounds": [0, 10]},
                },
                "objectives": [
                    {
                        "name": "minimize_distance",
                        "type": "minimize",
                        "function": "sqrt(x^2 + y^2)",
                        "weight": 1.0,
                        "variables": ["x", "y"],
                    }
                ],
            }

            response = await client.post("/api/v1/optimize", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "request_id" in data
            assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_invalid_request_handling():
    """Test handling of invalid requests."""
    from app.main import app

    with patch("app.api.endpoints.optimize.validate_api_key", return_value="test-key"):
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            # Test request without variables
            request_data = {"name": "Invalid Optimization", "objectives": []}

            response = await client.post("/api/v1/optimize", json=request_data)

            # Should fail validation
            assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test metrics endpoint."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/v1/optimize/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "active_optimizations" in data


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test optimization status endpoint."""
    from app.main import app

    with (
        patch("app.api.endpoints.optimize.validate_api_key", return_value="test-key"),
        patch("app.api.endpoints.optimize.RedisCache") as mock_cache_class,
    ):
        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "request_id": "test-request",
            "status": "completed",
            "progress": 100.0,
        }
        mock_cache_class.return_value = mock_cache

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/api/v1/optimize/test-request/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
