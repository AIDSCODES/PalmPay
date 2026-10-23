"""Integration tests for User API"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
import base64
import numpy as np
import cv2


def create_test_image() -> bytes:
    """Create a test image as bytes"""
    img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    cv2.circle(img, (112, 112), 80, (100, 50, 30), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    """Test successful user registration"""
    image_bytes = create_test_image()
    image_b64 = base64.b64encode(image_bytes).decode()

    files = [
        ("samples", ("palm1.jpg", image_bytes, "image/jpeg")),
        ("samples", ("palm2.jpg", image_bytes, "image/jpeg")),
        ("samples", ("palm3.jpg", image_bytes, "image/jpeg")),
    ]
    data = {"name": "Test User", "phone": "+1234567890"}

    response = await client.post("/api/v1/users/register", files=files, data=data)

    assert response.status_code == 201
    result = response.json()
    assert result["success"] is True
    assert "user_id" in result
    assert result["message"] == "User registered successfully"


@pytest.mark.asyncio
async def test_register_user_insufficient_samples(client: AsyncClient):
    """Test registration fails with too few samples"""
    image_bytes = create_test_image()

    files = [
        ("samples", ("palm1.jpg", image_bytes, "image/jpeg")),
        ("samples", ("palm2.jpg", image_bytes, "image/jpeg")),
    ]
    data = {"name": "Test User"}

    response = await client.post("/api/v1/users/register", files=files, data=data)

    assert response.status_code == 400
    result = response.json()
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, test_user):
    """Test getting user by ID"""
    response = await client.get(f"/api/v1/users/{test_user.id}")

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == str(test_user.id)
    assert result["name"] == test_user.name


@pytest.mark.asyncio
async def test_get_nonexistent_user(client: AsyncClient):
    """Test getting non-existent user"""
    response = await client.get(f"/api/v1/users/{uuid4()}")

    assert response.status_code == 404