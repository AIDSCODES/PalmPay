"""Unit tests for BiometricService"""
import pytest
from uuid import uuid4
import numpy as np
import base64
import cv2
from app.services.biometric_service import BiometricService
from app.ml.embedding import embedding_service
from app.utils.image import image_processor
from app.core.exceptions import ValidationError, BiometricError, ModelError


def create_mock_image() -> str:
    """Create a mock base64 encoded palm image"""
    img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    # Add some variation to make it look more like a palm
    cv2.circle(img, (112, 112), 80, (100, 50, 30), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()


@pytest.mark.asyncio
async def test_enroll_user_success(test_db, test_user):
    """Test successful biometric enrollment"""
    service = BiometricService(test_db)

    # Create 3 similar images
    images = [create_mock_image() for _ in range(3)]

    templates, quality_scores = await service.enroll_user(test_user.id, images)

    assert len(templates) == 3
    assert len(quality_scores) == 3
    assert all(q > 0.5 for q in quality_scores)


@pytest.mark.asyncio
async def test_enroll_user_insufficient_samples(test_db, test_user):
    """Test enrollment fails with too few samples"""
    service = BiometricService(test_db)
    images = [create_mock_image() for _ in range(2)]

    with pytest.raises(ValidationError, match="At least 3"):
        await service.enroll_user(test_user.id, images)


@pytest.mark.asyncio
async def test_enroll_user_too_many_samples(test_db, test_user):
    """Test enrollment fails with too many samples"""
    service = BiometricService(test_db)
    images = [create_mock_image() for _ in range(6)]

    with pytest.raises(ValidationError, match="Maximum 5"):
        await service.enroll_user(test_user.id, images)


@pytest.mark.asyncio
async def test_identify_user_no_match(test_db):
    """Test identification with no registered user"""
    service = BiometricService(test_db)
    image = create_mock_image()

    matched, user_id, similarity, reason = await service.identify(image)

    assert matched is False
    assert user_id is None
    assert reason == "NO_MATCH"


@pytest.mark.asyncio
async def test_verify_user_no_template(test_db, test_user):
    """Test verification for user without template"""
    service = BiometricService(test_db)
    image = create_mock_image()

    matched, similarity, reason = await service.verify_user(test_user.id, image)

    assert matched is False
    assert reason == "NO_TEMPLATE"