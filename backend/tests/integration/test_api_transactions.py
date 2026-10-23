"""Integration tests for Transaction API"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_transactions(client: AsyncClient, test_user):
    """Test getting transaction history"""
    response = await client.get(f"/api/v1/transactions/{test_user.id}")

    assert response.status_code == 200
    result = response.json()
    assert "transactions" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result


@pytest.mark.asyncio
async def test_get_transactions_pagination(client: AsyncClient, test_user):
    """Test transaction pagination"""
    response = await client.get(
        f"/api/v1/transactions/{test_user.id}",
        params={"page": 1, "page_size": 5}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["page"] == 1
    assert result["page_size"] == 5