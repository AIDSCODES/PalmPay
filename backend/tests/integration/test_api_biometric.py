"""Integration tests for Biometric API"""
import pytest
from httpx import AsyncClient
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
async def test_identify_no_match(client: AsyncClient):
    """Test identification with no registered biometric"""
    image_bytes = create_test_image()

    files = {"image": ("palm.jpg", image_bytes, "image/jpeg")}
    response = await client.post("/api/v1/biometric/identify", files=files)

    assert response.status_code == 200
    result = response.json()
    assert result["matched"] is False
    assert result["reason"] == "NO_MATCH"


@pytest.mark.asyncio
async def test_check_quality(client: AsyncClient):
    """Test image quality check"""
    image_bytes = create_test_image()

    files = {"image": ("palm.jpg", image_bytes, "image/jpeg")}
    response = await client.post("/api/v1/biometric/quality", files=files)

    assert response.status_code == 200
    result = response.json()
    assert "quality_score" in result
    assert "is_acceptable" in result