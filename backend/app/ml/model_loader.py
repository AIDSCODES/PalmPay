"""Model loader and registry"""
from typing import Dict, Optional
from app.ml.model import PalmEmbeddingModel, MockPalmEmbeddingModel, PalmVeinModel
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Registry for managing multiple model versions"""

    def __init__(self):
        self._models: Dict[str, PalmEmbeddingModel] = {}
        self._active_version: Optional[str] = None

    def register_model(self, version: str, model: PalmEmbeddingModel) -> None:
        """Register a model version"""
        self._models[version] = model
        logger.info(f"Registered model version: {version}")

    def get_model(self, version: str) -> Optional[PalmEmbeddingModel]:
        """Get a specific model version"""
        return self._models.get(version)

    def get_active_model(self) -> Optional[PalmEmbeddingModel]:
        """Get the currently active model"""
        if self._active_version:
            return self._models.get(self._active_version)
        return None

    def set_active_version(self, version: str) -> bool:
        """Set the active model version"""
        if version in self._models:
            self._active_version = version
            logger.info(f"Active model version set to: {version}")
            return True
        return False

    def list_versions(self) -> list[str]:
        """List all registered model versions"""
        return list(self._models.keys())

    def load_all(self) -> None:
        """Load all registered models"""
        for version, model in self._models.items():
            try:
                model.load()
                logger.info(f"Loaded model version: {version}")
            except Exception as e:
                logger.error(f"Failed to load model {version}: {e}")

    def unload_all(self) -> None:
        """Unload all models"""
        for version, model in self._models.items():
            try:
                model.unload()
                logger.info(f"Unloaded model version: {version}")
            except Exception as e:
                logger.error(f"Failed to unload model {version}: {e}")


# Global registry
model_registry = ModelRegistry()


def create_default_model() -> PalmEmbeddingModel:
    """Create the default model based on configuration"""
    if settings.USE_MOCK_MODEL:
        return MockPalmEmbeddingModel()
    else:
        return PalmVeinModel(settings.BIOMETRIC_MODEL_PATH)


def initialize_models() -> None:
    """Initialize models at startup"""
    default_model = create_default_model()
    model_registry.register_model(default_model.model_version, default_model)
    model_registry.set_active_version(default_model.model_version)
    model_registry.load_all()
    logger.info("Model initialization complete")