"""Integration tests for Device API"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_register_device(client: AsyncClient, test_db):
    """Test device registration (admin)"""
    from app.db.models.user import User, UserStatus
    from app.db.models.business import Business, BusinessStatus
    from uuid import uuid4
    
    # Create user and business
    user = User(name="Test Owner", phone="+1234567890", status=UserStatus.ACTIVE)
    test_db.add(user)
    await test_db.flush()
    
    business = Business(
        name="Test Business",
        owner_id=user.id,
        status=BusinessStatus.ACTIVE,
        verification_status="verified"
    )
    test_db.add(business)
    await test_db.flush()
    await test_db.commit()
    
    device_data = {
        "device_name": "Test ESP32",
        "business_id": str(business.id),
        "device_type": "ESP32"
    }
    headers = {"X-Admin-Key": ""}  # Default admin key is empty in test config

    response = await client.post("/api/v1/devices/register", json=device_data, headers=headers)

    assert response.status_code == 201
    result = response.json()
    assert "device_id" in result
    assert "device_key" in result
    assert result["message"] == "Device registered successfully. Save the device_key securely!"


@pytest.mark.asyncio
async def test_authenticate_device(client: AsyncClient, test_device):
    """Test device authentication"""
    device, device_key = test_device

    auth_data = {
        "device_id": str(device.id),
        "device_key": device_key
    }

    response = await client.post("/api/v1/devices/authenticate", json=auth_data)

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == str(device.id)
    assert result["pairing_status"] == "PAIRED"
    assert result["connection_status"] == "ONLINE"


@pytest.mark.asyncio
async def test_authenticate_device_invalid_key(client: AsyncClient, test_device):
    """Test authentication with invalid key"""
    device, _ = test_device

    auth_data = {
        "device_id": str(device.id),
        "device_key": "wrong-key"
    }

    response = await client.post("/api/v1/devices/authenticate", json=auth_data)

    assert response.status_code == 401
    result = response.json()
    assert result["error"]["code"] == "DEVICE_UNAUTHORIZED"