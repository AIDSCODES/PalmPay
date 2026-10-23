"""Subscription schemas"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.db.models.subscription import SubscriptionPlan, SubscriptionStatus, BillingInterval


class SubscriptionBase(BaseModel):
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")


class SubscriptionCreate(SubscriptionBase):
    business_id: UUID
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    trial_days: Optional[int] = Field(None, ge=0)


class SubscriptionUpdate(BaseModel):
    plan: Optional[SubscriptionPlan] = None
    billing_interval: Optional[BillingInterval] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    cancel_at_period_end: Optional[bool] = None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    business_id: UUID
    status: SubscriptionStatus
    billing_interval: BillingInterval
    trial_started_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    provider: Optional[str] = None
    provider_subscription_id: Optional[str] = None
    provider_customer_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    subscriptions: List["SubscriptionResponse"]
    total: int
    page: int
    page_size: int