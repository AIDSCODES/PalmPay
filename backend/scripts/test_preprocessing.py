#!/usr/bin/env python
"""Test image preprocessing"""
import sys
from pathlib import Path
import base64
import numpy as np
import cv2

sys.path.append(str(Path(__file__).parent.parent))

from app.utils.image import image_processor
from app.core.logging import setup_logging

setup_logging()


def create_test_image() -> str:
    """Create a test image"""
    img = np.random.randint(50, 200, (400, 400, 3), dtype=np.uint8)
    cv2.circle(img, (200, 200), 150, (100, 50, 30), -1)
    cv2.circle(img, (200, 200), 100, (80, 40, 20), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()


def main():
    """Test image preprocessing"""
    print("Testing image preprocessing...")

    # Create test image
    b64_image = create_test_image()
    print(f"Created test image (base64 length: {len(b64_image)})")

    # Test preprocessing
    try:
        processed = image_processor.preprocess(b64_image)
        print(f"Preprocessed shape: {processed.shape}")
        print(f"Preprocessed dtype: {processed.dtype}")
        print(f"Preprocessed range: [{processed.min():.3f}, {processed.max():.3f}]")
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        sys.exit(1)

    # Test quality assessment
    decoded = image_processor.decode_base64_image(b64_image)
    quality = image_processor.assess_quality(decoded)
    print(f"Quality score: {quality:.3f}")

    is_valid, issues = image_processor.validate_image(decoded)
    print(f"Valid: {is_valid}")
    if issues:
        print(f"Issues: {issues}")

    print("All tests passed!")


if __name__ == "__main__":
    main()