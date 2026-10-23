"""Integration tests for Payment API"""
import pytest
from httpx import AsyncClient
from decimal import Decimal
from uuid import uuid4


@pytest.mark.asyncio
async def test_payment_success(client: AsyncClient, test_user, test_wallet, test_device):
    """Test successful payment"""
    device, device_key = test_device
    payment_data = {
        "user_id": str(test_user.id),
        "amount": "100.00",
        "currency": "INR"
    }
    headers = {
        "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000",
        "X-Device-ID": str(device.id),
        "X-Device-Key": device_key
    }

    response = await client.post("/api/v1/payments", json=payment_data, headers=headers)

    assert response.status_code == 201
    result = response.json()
    assert result["success"] is True
    assert result["amount"] == "100.00"
    assert "transaction_id" in result


@pytest.mark.asyncio
async def test_payment_insufficient_balance(client: AsyncClient, test_user, test_wallet, test_device):
    """Test payment with insufficient balance"""
    device, device_key = test_device
    payment_data = {
        "user_id": str(test_user.id),
        "amount": "2000.00",
        "currency": "INR"
    }
    headers = {
        "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174001",
        "X-Device-ID": str(device.id),
        "X-Device-Key": device_key
    }

    response = await client.post("/api/v1/payments", json=payment_data, headers=headers)

    assert response.status_code == 400
    result = response.json()
    assert result["success"] is False
    assert result["error"]["code"] == "WALLET_ERROR"


@pytest.mark.asyncio
async def test_payment_idempotency(client: AsyncClient, test_user, test_wallet, test_device):
    """Test idempotent payment processing"""
    device, device_key = test_device
    payment_data = {
        "user_id": str(test_user.id),
        "amount": "100.00",
        "currency": "INR"
    }
    idempotency_key = "123e4567-e89b-12d3-a456-426614174002"
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Device-ID": str(device.id),
        "X-Device-Key": device_key
    }

    # First request
    response1 = await client.post("/api/v1/payments", json=payment_data, headers=headers)
    assert response1.status_code == 201
    result1 = response1.json()

    # Second request with same idempotency key
    response2 = await client.post("/api/v1/payments", json=payment_data, headers=headers)
    assert response2.status_code == 201
    result2 = response2.json()

    # Should return same transaction
    assert result1["transaction_id"] == result2["transaction_id"]


@pytest.mark.asyncio
async def test_payment_missing_idempotency_key(client: AsyncClient, test_user, test_wallet, test_device):
    """Test payment without idempotency key"""
    device, device_key = test_device
    payment_data = {
        "user_id": str(test_user.id),
        "amount": "100.00",
        "currency": "INR"
    }
    headers = {
        "X-Device-ID": str(device.id),
        "X-Device-Key": device_key
    }

    response = await client.post("/api/v1/payments", json=payment_data, headers=headers)

    # Should still work (idempotency key is optional but recommended)
    assert response.status_code == 201