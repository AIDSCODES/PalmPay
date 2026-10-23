"""Consent record schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.db.models.consent import ConsentType, ConsentStatus


class ConsentRecordBase(BaseModel):
    consent_type: ConsentType
    policy_version: str = Field(..., max_length=50)
    policy_content: Optional[str] = None


class ConsentRecordCreate(ConsentRecordBase):
    user_id: UUID
    expires_at: Optional[datetime] = None
    consent_metadata: Optional[dict] = None


class ConsentRecordUpdate(BaseModel):
    status: Optional[str] = None
    revocation_reason: Optional[str] = None
    revoked_by: Optional[UUID] = None


class ConsentRecordResponse(ConsentRecordBase):
    id: UUID
    user_id: UUID
    status: ConsentStatus
    consent_given_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    revocation_reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    consent_metadata: dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConsentRecordListResponse(BaseModel):
    consents: List["ConsentRecordResponse"]
    total: int
    page: int
    page_size: int


class ConsentRevokeRequest(BaseModel):
    consent_type: ConsentType
    revocation_reason: Optional[str] = None