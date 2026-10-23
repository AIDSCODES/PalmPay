"""Transaction schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.db.models.transaction import TransactionType, TransactionStatus


class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    transaction_type: TransactionType


class TransactionCreate(TransactionBase):
    user_id: UUID
    wallet_id: UUID
    merchant_id: Optional[UUID] = None
    description: Optional[str] = None
    idempotency_key: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: UUID
    transaction_reference: str
    user_id: UUID
    wallet_id: UUID
    merchant_id: Optional[UUID] = None
    status: TransactionStatus
    description: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentRequest(BaseModel):
    """Payment request from ESP32"""
    user_id: UUID
    amount: Decimal
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    merchant_id: Optional[UUID] = None
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    """Payment response"""
    success: bool
    transaction_id: Optional[str] = None
    transaction_reference: Optional[str] = None
    amount: Optional[Decimal] = None
    remaining_balance: Optional[Decimal] = None
    message: str
    request_id: str


class TransactionFilter(BaseModel):
    """Transaction filter parameters"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[TransactionStatus] = None
    transaction_type: Optional[TransactionType] = None
    merchant_id: Optional[UUID] = None


class TransactionListResponse(BaseModel):
    """Transaction list response"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int