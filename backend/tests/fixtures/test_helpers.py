"""Test utilities and helpers"""
import base64
import numpy as np
import cv2
from typing import List
from decimal import Decimal
from uuid import uuid4
from app.db.models.user import User, UserStatus
from app.db.models.wallet import Wallet, WalletStatus
from app.db.models.device import Device, DeviceStatus
from app.core.security import hash_device_key, generate_device_key


def create_test_image_base64(size: tuple = (224, 224)) -> str:
    """Create a test palm-like image as base64"""
    img = np.random.randint(50, 200, (*size, 3), dtype=np.uint8)
    # Add palm-like pattern
    center = (size[1] // 2, size[0] // 2)
    cv2.circle(img, center, min(size) // 3, (100, 50, 30), -1)
    cv2.circle(img, center, min(size) // 5, (80, 40, 20), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()


def create_test_image_bytes(size: tuple = (224, 224)) -> bytes:
    """Create a test palm-like image as bytes"""
    img = np.random.randint(50, 200, (*size, 3), dtype=np.uint8)
    center = (size[1] // 2, size[0] // 2)
    cv2.circle(img, center, min(size) // 3, (100, 50, 30), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


def create_mock_user(
    name: str = "Test User",
    phone: str = None,
    status: UserStatus = UserStatus.ACTIVE
) -> User:
    """Create a mock user object"""
    return User(
        id=uuid4(),
        name=name,
        phone=phone,
        status=status
    )


def create_mock_wallet(
    user_id,
    balance: Decimal = Decimal("1000.00"),
    currency: str = "INR",
    status: WalletStatus = WalletStatus.ACTIVE
) -> Wallet:
    """Create a mock wallet object"""
    return Wallet(
        id=uuid4(),
        user_id=user_id,
        balance=balance,
        currency=currency,
        status=status
    )


def create_mock_device(
    name: str = "Test ESP32",
    status: DeviceStatus = DeviceStatus.ACTIVE
) -> tuple[Device, str]:
    """Create a mock device with key"""
    device_key = generate_device_key()
    device = Device(
        id=uuid4(),
        device_name=name,
        device_key_hash=hash_device_key(device_key),
        status=status
    )
    return device, device_key


def assert_response_success(response, expected_status=200):
    """Assert response is successful"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("success") is True, f"Response not successful: {data}"
    return data


def assert_response_error(response, expected_status=400, expected_code=None):
    """Assert response is an error"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("success") is False, f"Response should be error: {data}"
    if expected_code:
        assert data.get("error", {}).get("code") == expected_code, f"Expected error code {expected_code}"
    return data