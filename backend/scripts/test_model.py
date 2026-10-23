#!/usr/bin/env python
"""Test ML model"""
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from app.ml.embedding import embedding_service
from app.ml.model import MockPalmEmbeddingModel
from app.utils.image import image_processor
import base64
import cv2


def create_test_image() -> str:
    """Create a test image"""
    img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    cv2.circle(img, (112, 112), 80, (100, 50, 30), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()


def main():
    """Test ML model"""
    print("Testing ML model...")

    # Check model
    print(f"Model version: {embedding_service.model_version}")
    print(f"Embedding dim: {embedding_service.embedding_dim}")
    print(f"Model type: {type(embedding_service.model).__name__}")

    # Create test image
    b64_image = create_test_image()

    # Preprocess
    preprocessed = image_processor.preprocess(b64_image)
    print(f"Preprocessed shape: {preprocessed.shape}")

    # Generate embedding
    embedding = embedding_service.generate_embedding(preprocessed)
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding norm: {np.linalg.norm(embedding):.6f}")

    # Test consistency
    embeddings = [embedding_service.generate_embedding(preprocessed) for _ in range(3)]
    consistent, avg_sim, min_sim = embedding_service.check_consistency(embeddings)
    print(f"Consistency check: consistent={consistent}, avg_sim={avg_sim:.4f}, min_sim={min_sim:.4f}")

    # Test similarity
    sim = embedding_service.compute_similarity(embeddings[0], embeddings[1])
    print(f"Self-similarity: {sim:.6f}")

    print("All tests passed!")


if __name__ == "__main__":
    main()