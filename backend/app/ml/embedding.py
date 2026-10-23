"""Embedding generation service"""
import numpy as np
from typing import List
from app.ml.model import PalmEmbeddingModel, MockPalmEmbeddingModel, PalmVeinModel
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ModelError

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating palm vein embeddings"""

    def __init__(self):
        self._model: Optional[PalmEmbeddingModel] = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the embedding model based on configuration"""
        if settings.USE_MOCK_MODEL:
            logger.warning("Initializing MOCK model - NOT FOR PRODUCTION")
            self._model = MockPalmEmbeddingModel()
        else:
            logger.info("Initializing production palm vein model")
            self._model = PalmVeinModel(settings.BIOMETRIC_MODEL_PATH)

        self._model.load()

    @property
    def model(self) -> PalmEmbeddingModel:
        """Get the current model instance"""
        if self._model is None:
            raise ModelError("Model not initialized")
        return self._model

    @property
    def model_version(self) -> str:
        """Get current model version"""
        return self.model.model_version

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.model.embedding_dim

    def generate_embedding(self, preprocessed_image: np.ndarray) -> np.ndarray:
        """Generate embedding from preprocessed image"""
        return self.model.generate_embedding(preprocessed_image)

    def generate_embeddings_batch(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Generate embeddings for multiple images"""
        return [self.generate_embedding(img) for img in images]

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        # Ensure embeddings are normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(np.clip(similarity, -1.0, 1.0))

    def check_consistency(self, embeddings: List[np.ndarray], threshold: float = 0.8) -> tuple:
        """
        Check consistency between enrollment embeddings.

        Returns:
            (is_consistent: bool, avg_similarity: float, min_similarity: float)
        """
        if len(embeddings) < 2:
            return True, 1.0, 1.0

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = self.compute_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)

        avg_sim = np.mean(similarities)
        min_sim = np.min(similarities)

        return min_sim >= threshold, float(avg_sim), float(min_sim)

    def reload_model(self) -> None:
        """Reload the model (e.g., after update)"""
        if self._model:
            self._model.unload()
        self._initialize_model()


# Global instance
embedding_service = EmbeddingService()