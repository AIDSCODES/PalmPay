"""Payment request schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.db.models.payment_request import PaymentRequestStatus


class PaymentRequestBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    description: Optional[str] = None
    expires_at: datetime


class PaymentRequestCreate(PaymentRequestBase):
    business_id: UUID
    branch_id: UUID
    device_id: Optional[UUID] = None
    idempotency_key: Optional[str] = Field(None, max_length=100)


class PaymentRequestUpdate(BaseModel):
    status: Optional[str] = None
    failure_reason: Optional[str] = None


class PaymentRequestResponse(BaseModel):
    id: UUID
    request_reference: str
    business_id: UUID
    branch_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    created_by: UUID
    amount: Decimal
    currency: str
    description: Optional[str] = None
    status: str
    idempotency_key: Optional[str] = None
    sent_to_device_at: Optional[datetime] = None
    device_acknowledged_at: Optional[datetime] = None
    customer_identified_at: Optional[datetime] = None
    customer_user_id: Optional[UUID] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    expires_at: datetime
    transaction_id: Optional[UUID] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentRequestListResponse(BaseModel):
    payment_requests: List["PaymentRequestResponse"]
    total: int
    page: int
    page_size: int


# Payment request state transition validation
VALID_STATUS_TRANSITIONS = {
    "CREATED": ["SENT_TO_DEVICE", "CANCELLED", "EXPIRED"],
    "SENT_TO_DEVICE": ["AWAITING_CUSTOMER", "CANCELLED", "EXPIRED"],
    "AWAITING_CUSTOMER": ["PROCESSING", "CANCELLED", "EXPIRED"],
    "PROCESSING": ["SUCCEEDED", "FAILED"],
    "SUCCEEDED": [],
    "FAILED": [],
    "CANCELLED": [],
    "EXPIRED": [],
}


def can_transition(current_status: str, new_status: str) -> bool:
    """Check if state transition is valid"""
    valid_transitions = {
        "CREATED": ["SENT_TO_DEVICE", "CANCELLED", "EXPIRED"],
        "SENT_TO_DEVICE": ["AWAITING_CUSTOMER", "CANCELLED", "EXPIRED"],
        "AWAITING_CUSTOMER": ["PROCESSING", "CANCELLED", "EXPIRED"],
        "PROCESSING": ["SUCCEEDED", "FAILED"],
        "SUCCEEDED": [],
        "FAILED": [],
        "CANCELLED": [],
        "EXPIRED": [],
    }
    return new_status in valid_transitions.get(current_status, [])