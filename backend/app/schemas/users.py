"""User schemas"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from app.db.models.user import UserStatus


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")


class UserCreate(UserBase):
    pass


class UserCreateInternal(UserCreate):
    """Internal user creation (from device registration)"""
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    id: UUID
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRegisterRequest(BaseModel):
    """User registration request from ESP32"""
    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")


class UserRegisterResponse(BaseModel):
    """User registration response"""
    success: bool
    user_id: UUID
    message: str
    request_id: str


class UserListResponse(BaseModel):
    """User list response for admin"""
    users: list[UserResponse]
    total: int
    page: int
    page_size: int