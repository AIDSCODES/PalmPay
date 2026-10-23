"""Integration tests for Health API"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] in ["ok", "degraded"]
    assert "database" in result
    assert "model" in result
    assert "version" in result
    assert "environment" in result