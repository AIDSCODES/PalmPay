"""ML Model abstraction and placeholder implementation"""
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ModelError

logger = get_logger(__name__)


class PalmEmbeddingModel(ABC):
    """Abstract base class for palm vein embedding models"""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return model version identifier"""
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return embedding dimension"""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load the model"""
        pass

    @abstractmethod
    def generate_embedding(self, preprocessed_image: np.ndarray) -> np.ndarray:
        """
        Generate embedding from preprocessed image.

        Args:
            preprocessed_image: Preprocessed image tensor (1, C, H, W)

        Returns:
            Embedding vector of shape (embedding_dim,)
        """
        pass

    @abstractmethod
    def validate_input(self, image: np.ndarray) -> bool:
        """Validate input image tensor"""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model and free resources"""
        pass


class MockPalmEmbeddingModel(PalmEmbeddingModel):
    """
    DEVELOPMENT-ONLY MOCK MODEL

    ⚠️  WARNING: This is a PLACEHOLDER for development and testing ONLY.
    ⚠️  DO NOT USE IN PRODUCTION.
    ⚠️  This does NOT provide real biometric authentication.
    ⚠️  Replace with actual trained palm vein model before deployment.
    """

    def __init__(self):
        self._loaded = False
        self._model_version = "mock_palm_model_v1"
        self._embedding_dim = settings.BIOMETRIC_EMBEDDING_DIM
        logger.warning("=" * 60)
        logger.warning("USING MOCK PALM VEIN MODEL - NOT FOR PRODUCTION USE")
        logger.warning("=" * 60)

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def load(self) -> None:
        """Load mock model"""
        self._loaded = True
        logger.info("Mock palm vein model loaded")

    def generate_embedding(self, preprocessed_image: np.ndarray) -> np.ndarray:
        """Generate deterministic mock embedding based on image content"""
        if not self._loaded:
            raise ModelError("Model not loaded")

        if not self.validate_input(preprocessed_image):
            raise ModelError("Invalid input tensor")

        # Use image content to generate deterministic embedding
        # This ensures same image -> same embedding (for testing)
        image_hash = hash(preprocessed_image.tobytes())
        np.random.seed(abs(image_hash) % (2**32))

        # Generate normalized embedding
        embedding = np.random.randn(self._embedding_dim).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def validate_input(self, image: np.ndarray) -> bool:
        """Validate input tensor shape"""
        expected_shape = (1, 3, settings.IMAGE_TARGET_SIZE[0], settings.IMAGE_TARGET_SIZE[1])
        return image.shape == expected_shape

    def unload(self) -> None:
        """Unload mock model"""
        self._loaded = False
        logger.info("Mock palm vein model unloaded")


class PalmVeinModel(PalmEmbeddingModel):
    """
    Production Palm Vein Model (PyTorch implementation)
    
    Uses ResNet34 backbone with embedding head matching the training architecture.
    """

    def __init__(self, model_path: str):
        self._model_path = model_path
        self._model = None
        self._device = None
        self._loaded = False
        self._model_version = settings.BIOMETRIC_MODEL_VERSION
        self._embedding_dim = settings.BIOMETRIC_EMBEDDING_DIM

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def load(self) -> None:
        """Load the trained PyTorch model"""
        try:
            import torch
            import torch.nn as nn
            from torchvision.models import resnet34, ResNet34_Weights

            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Build the exact same architecture as training (PalmVeinEncoder)
            # Backbone: ResNet34 with pretrained weights
            backbone = resnet34(weights=ResNet34_Weights.IMAGENET1K_V1)
            backbone.fc = nn.Identity()  # Remove classification head
            backbone_dim = 512

            # Embedding head matching training architecture
            embedding_head = nn.Sequential(
                nn.Dropout(0.1),
                nn.Linear(backbone_dim, self._embedding_dim),
                nn.BatchNorm1d(self._embedding_dim)
            )

            # Combine into single model matching training architecture
            class PalmVeinEncoder(nn.Module):
                def __init__(self, backbone, embedding_head):
                    super().__init__()
                    self.backbone = backbone
                    self.embedding_head = embedding_head

                def forward(self, x):
                    features = self.backbone(x)
                    embedding = self.embedding_head(features)
                    return torch.nn.functional.normalize(embedding, p=2, dim=1)

            self._model = PalmVeinEncoder(
                backbone=backbone,
                embedding_head=nn.Sequential(
                    nn.Dropout(0.1),
                    nn.Linear(512, self._embedding_dim),
                    nn.BatchNorm1d(self._embedding_dim)
                )
            )

            # Load trained weights
            state_dict = torch.load(self._model_path, map_location=self._device)
            if 'model_state_dict' in state_dict:
                self._model.load_state_dict(state_dict['model_state_dict'])
            else:
                self._model.load_state_dict(state_dict)

            self._model.to(self._device)
            self._model.eval()

            self._loaded = True
            logger.info(f"Palm vein model loaded from {self._model_path} on {self._device}")

        except Exception as e:
            logger.error(f"Failed to load palm vein model: {e}")
            raise ModelError(f"Model loading failed: {e}")

    def generate_embedding(self, preprocessed_image: np.ndarray) -> np.ndarray:
        """Generate embedding using the trained model"""
        if not self._loaded:
            raise ModelError("Model not loaded")

        if not self.validate_input(preprocessed_image):
            raise ModelError("Invalid input tensor")

        try:
            import torch

            with torch.no_grad():
                # Convert to tensor
                input_tensor = torch.from_numpy(preprocessed_image).to(self._device)

                # Forward pass
                embedding = self._model(input_tensor)

                # Convert to numpy
                embedding = embedding.cpu().numpy().squeeze()

                # L2 normalize
                embedding = embedding / np.linalg.norm(embedding)

            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise ModelError(f"Inference failed: {e}")

    def validate_input(self, image: np.ndarray) -> bool:
        """Validate input tensor shape"""
        expected_shape = (1, 3, settings.IMAGE_TARGET_SIZE[0], settings.IMAGE_TARGET_SIZE[1])
        return image.shape == expected_shape

    def unload(self) -> None:
        """Unload model and free GPU memory"""
        if self._model is not None:
            import torch
            del self._model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        self._loaded = False
        logger.info("Palm vein model unloaded")