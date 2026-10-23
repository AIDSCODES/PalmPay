"""Device schemas"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.db.models.device import DeviceStatus


class DeviceBase(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=255)


class DeviceCreate(DeviceBase):
    pass


class DeviceRegisterRequest(BaseModel):
    """Device registration request (admin)"""
    device_name: str = Field(..., min_length=1, max_length=255)


class DeviceRegisterResponse(BaseModel):
    """Device registration response with generated key"""
    device_id: UUID
    device_key: str  # Only returned once!
    message: str


class DeviceAuthRequest(BaseModel):
    """Device authentication request"""
    device_id: UUID
    device_key: str


class DeviceResponse(BaseModel):
    id: UUID
    device_name: str
    status: DeviceStatus
    last_seen: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Device list response for admin"""
    devices: list[DeviceResponse]
    total: int
    page: int
    page_size: int