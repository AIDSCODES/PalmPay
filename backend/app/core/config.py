"""Application configuration using Pydantic Settings"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "PalmPay"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://palmpay:palmpay@localhost:5432/palmpay",
        description="PostgreSQL connection URL with pgvector"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Biometric
    BIOMETRIC_MATCH_THRESHOLD: float = Field(
        default=0.85,
        description="Cosine similarity threshold for biometric matching (0.0-1.0)"
    )
    BIOMETRIC_MODEL_PATH: str = Field(
        default="model/palm_vein_model.pt",
        description="Path to the trained palm vein model"
    )
    BIOMETRIC_MODEL_VERSION: str = Field(
        default="palm_model_v1",
        description="Version identifier for the biometric model"
    )
    BIOMETRIC_EMBEDDING_DIM: int = Field(
        default=512,
        description="Dimension of the embedding vector"
    )
    BIOMETRIC_QUALITY_THRESHOLD: float = Field(
        default=0.6,
        description="Minimum quality score for enrollment/identification"
    )
    BIOMETRIC_MAX_SAMPLES: int = Field(
        default=5,
        description="Maximum number of enrollment samples"
    )
    BIOMETRIC_MIN_SAMPLES: int = Field(
        default=3,
        description="Minimum number of enrollment samples"
    )

    # Image Processing
    IMAGE_MAX_SIZE_MB: int = Field(default=10, description="Maximum image size in MB")
    IMAGE_ALLOWED_FORMATS: List[str] = Field(
        default=["jpeg", "jpg", "png", "bmp"],
        description="Allowed image formats"
    )
    IMAGE_TARGET_SIZE: tuple = Field(
        default=(224, 224),
        description="Target image size for model input (height, width)"
    )

    # Security
    DEVICE_AUTH_SECRET: str = Field(
        default="",
        description="Secret key for device authentication (HMAC)"
    )
    JWT_SECRET_KEY: str = Field(
        default="",
        description="Secret key for JWT tokens"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiry in minutes")
    ADMIN_API_KEY: str = Field(default="", description="API key for admin endpoints")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per window")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, description="Rate limit window in seconds")
    RATE_LIMIT_LOGIN_ATTEMPTS: int = Field(default=5, description="Max login attempts per window")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # Idempotency
    IDEMPOTENCY_TTL_HOURS: int = Field(default=24, description="Idempotency key TTL in hours")

    # Wallet
    DEFAULT_CURRENCY: str = Field(default="INR", description="Default currency code")
    INITIAL_WALLET_BALANCE: float = Field(default=0.0, description="Initial wallet balance for new users")

    # Model (Development/Placeholder)
    USE_MOCK_MODEL: bool = Field(
        default=False,
        description="Use mock model for development (MUST be False in production)"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()