"""Staff/Cashier schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from app.db.models.staff import StaffRole, StaffStatus


class BusinessStaffBase(BaseModel):
    user_id: UUID
    branch_id: Optional[UUID] = None
    role: StaffRole = StaffRole.CASHIER


class BusinessStaffCreate(BusinessStaffBase):
    pass


class BusinessStaffUpdate(BaseModel):
    branch_id: Optional[UUID] = None
    role: Optional[StaffRole] = None
    status: Optional[StaffStatus] = None


class BusinessStaffResponse(BusinessStaffBase):
    id: UUID
    business_id: UUID
    branch_id: Optional[UUID] = None
    status: StaffStatus
    invited_by: Optional[UUID] = None
    joined_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessStaffListResponse(BaseModel):
    staff: List["BusinessStaffResponse"]
    total: int
    page: int
    page_size: int