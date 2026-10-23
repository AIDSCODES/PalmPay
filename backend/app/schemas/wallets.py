"""Wallet schemas"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.db.models.wallet import WalletStatus


class WalletBase(BaseModel):
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")


class WalletCreate(WalletBase):
    user_id: UUID
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class WalletResponse(WalletBase):
    id: UUID
    user_id: UUID
    balance: Decimal
    status: WalletStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTopUpRequest(BaseModel):
    """Wallet top-up request (admin only)"""
    amount: Decimal = Field(..., gt=0, description="Amount to add")
    description: Optional[str] = None


class WalletBalanceResponse(BaseModel):
    """Wallet balance response"""
    user_id: UUID
    balance: Decimal
    currency: str
    status: WalletStatus