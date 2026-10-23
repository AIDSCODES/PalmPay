"""Biometric schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class BiometricTemplateBase(BaseModel):
    model_version: str
    quality_score: float = Field(..., ge=0.0, le=1.0)


class BiometricTemplateCreate(BiometricTemplateBase):
    user_id: UUID
    embedding: List[float] = Field(..., min_length=512, max_length=512)


class BiometricTemplateResponse(BiometricTemplateBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BiometricIdentifyRequest(BaseModel):
    """Biometric identification request from ESP32"""
    image: str = Field(..., description="Base64 encoded palm image")


class BiometricIdentifyResponse(BaseModel):
    """Biometric identification response"""
    matched: bool
    user_id: Optional[UUID] = None
    similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    reason: Optional[str] = None
    request_id: str


class BiometricEnrollmentRequest(BaseModel):
    """Biometric enrollment request (multiple samples)"""
    images: List[str] = Field(..., min_length=3, max_length=5, description="List of base64 encoded palm images")


class BiometricEnrollmentResponse(BaseModel):
    """Biometric enrollment response"""
    success: bool
    user_id: Optional[UUID] = None
    quality_scores: Optional[List[float]] = None
    message: str
    request_id: str


class BiometricQualityCheckResponse(BaseModel):
    """Image quality check response"""
    quality_score: float
    is_acceptable: bool
    issues: List[str] = []