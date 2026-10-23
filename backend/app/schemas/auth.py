"""Authentication schemas"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.db.models.user import UserStatus


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email address or phone number")
    password: str = Field(..., min_length=4, description="User password")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="User password")
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")


class UserAuthResponse(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: UserStatus
    role: str = "merchant_owner"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserAuthResponse
