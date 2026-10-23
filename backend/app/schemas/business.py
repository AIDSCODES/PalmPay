"""Business schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.db.models.business import BusinessStatus, BranchStatus


class BusinessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    business_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    address: Optional[str] = None
    gst_number: Optional[str] = Field(None, max_length=50)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    business_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    address: Optional[str] = None
    gst_number: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None


class BusinessResponse(BusinessBase):
    id: UUID
    owner_id: UUID
    status: BusinessStatus
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessListResponse(BaseModel):
    businesses: List[BusinessResponse]
    total: int
    page: int
    page_size: int


# Branch schemas
class BranchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    email: Optional[EmailStr] = None


class BranchCreate(BranchBase):
    business_id: UUID


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    email: Optional[EmailStr] = None
    status: Optional[BranchStatus] = None


class BranchResponse(BranchBase):
    id: UUID
    business_id: UUID
    status: BranchStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BranchListResponse(BaseModel):
    branches: List[BranchResponse]
    total: int
    page: int
    page_size: int