"""Tests for main FastAPI application."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_root_endpoint(async_client: AsyncClient) -> None:
    """Test root endpoint returns API info."""
    response = await async_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "health" in data


@pytest.mark.unit
async def test_health_check(async_client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data


@pytest.mark.unit
async def test_metrics_endpoint(async_client: AsyncClient) -> None:
    """Test Prometheus metrics endpoint."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


@pytest.mark.unit
async def test_404_handler(async_client: AsyncClient) -> None:
    """Test 404 handler."""
    response = await async_client.get("/nonexistent")
    assert response.status_code == 404
