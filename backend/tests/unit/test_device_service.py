"""Unit tests for DeviceService"""
import pytest
from uuid import uuid4
from app.services.device_service import DeviceService
from app.schemas.devices import DeviceRegisterRequest
from app.db.models.device import DeviceStatus
from app.core.exceptions import NotFoundError, DeviceError


@pytest.mark.asyncio
async def test_register_device(test_db):
    """Test device registration"""
    service = DeviceService(test_db)
    request = DeviceRegisterRequest(device_name="Test ESP32")

    device, device_key = await service.register_device(request)

    assert device.device_name == "Test ESP32"
    assert device.status == DeviceStatus.PENDING
    assert device_key is not None
    assert len(device_key) > 0


@pytest.mark.asyncio
async def test_authenticate_device_success(test_db):
    """Test successful device authentication"""
    service = DeviceService(test_db)
    request = DeviceRegisterRequest(device_name="Test ESP32")
    device, device_key = await service.register_device(request)

    # Activate device first
    await service.activate_device(device.id)

    # Authenticate
    auth_device = await service.authenticate_device(device.id, device_key)

    assert auth_device.id == device.id
    assert auth_device.status == DeviceStatus.ACTIVE


@pytest.mark.asyncio
async def test_authenticate_device_invalid_key(test_db):
    """Test authentication with invalid key"""
    service = DeviceService(test_db)
    request = DeviceRegisterRequest(device_name="Test ESP32")
    device, _ = await service.register_device(request)

    with pytest.raises(DeviceError, match="Invalid device key"):
        await service.authenticate_device(device.id, "wrong-key")


@pytest.mark.asyncio
async def test_authenticate_revoked_device(test_db):
    """Test authentication fails for revoked device"""
    service = DeviceService(test_db)
    request = DeviceRegisterRequest(device_name="Test ESP32")
    device, device_key = await service.register_device(request)

    await service.activate_device(device.id)
    await service.revoke_device(device.id)

    with pytest.raises(DeviceError, match="Device has been revoked"):
        await service.authenticate_device(device.id, device_key)


@pytest.mark.asyncio
async def test_revoke_device(test_db):
    """Test device revocation"""
    service = DeviceService(test_db)
    request = DeviceRegisterRequest(device_name="Test ESP32")
    device, _ = await service.register_device(request)

    revoked = await service.revoke_device(device.id)
    assert revoked.status == DeviceStatus.REVOKED