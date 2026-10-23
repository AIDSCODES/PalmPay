"""Integration tests for Wallet API"""
import pytest
from httpx import AsyncClient
from decimal import Decimal


@pytest.mark.asyncio
async def test_get_wallet(client: AsyncClient, test_user, test_wallet):
    """Test getting wallet balance"""
    response = await client.get(f"/api/v1/wallets/{test_user.id}")

    assert response.status_code == 200
    result = response.json()
    assert result["user_id"] == str(test_user.id)
    assert result["balance"] == "1000.00"
    assert result["currency"] == "INR"


@pytest.mark.asyncio
async def test_get_nonexistent_wallet(client: AsyncClient):
    """Test getting non-existent wallet"""
    from uuid import uuid4
    response = await client.get(f"/api/v1/wallets/{uuid4()}")

    assert response.status_code == 404