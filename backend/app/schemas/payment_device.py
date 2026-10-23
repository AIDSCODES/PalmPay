"""Payment device schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.db.models.payment_device import DeviceType, PairingStatus, ConnectionStatus


class PaymentDeviceBase(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=255)
    device_type: DeviceType = DeviceType.ESP32
    firmware_version: Optional[str] = Field(None, max_length=50)


class PaymentDeviceCreate(PaymentDeviceBase):
    business_id: UUID
    branch_id: Optional[UUID] = None


class PaymentDeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(None, min_length=1, max_length=255)
    firmware_version: Optional[str] = Field(None, max_length=50)
    branch_id: Optional[UUID] = None
    pairing_status: Optional[str] = None
    connection_status: Optional[str] = None


class PaymentDeviceResponse(PaymentDeviceBase):
    id: UUID
    business_id: UUID
    branch_id: Optional[UUID] = None
    pairing_status: PairingStatus
    paired_at: Optional[datetime] = None
    paired_by: Optional[UUID] = None
    connection_status: ConnectionStatus
    last_seen: Optional[datetime] = None
    ip_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentDeviceListResponse(BaseModel):
    devices: List["PaymentDeviceResponse"]
    total: int
    page: int
    page_size: int


# Rebuild models to resolve forward references
PaymentDeviceListResponse.model_rebuild()


class DevicePairRequest(BaseModel):
    device_id: UUID
    device_key: str


class DeviceHeartbeatRequest(BaseModel):
    ip_address: Optional[str] = Field(None, max_length=45)
    metadata: Optional[str] = None


class PaymentDeviceRegisterResponse(BaseModel):
    device_id: UUID
    device_key: str
    message: str