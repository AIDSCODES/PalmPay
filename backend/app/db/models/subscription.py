"""Subscription model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Numeric, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class SubscriptionPlan(str, PyEnum):
    FREE = "FREE"
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    TRIALING = "TRIALING"


class BillingInterval(str, PyEnum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan),
        default=SubscriptionPlan.FREE,
        nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )
    billing_interval: Mapped[BillingInterval] = mapped_column(
        Enum(BillingInterval),
        default=BillingInterval.MONTHLY,
        nullable=False
    )
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Trial
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Billing cycle
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Provider integration
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cancellation
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Metadata
    subscription_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscriptions_business_id", "business_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_provider_subscription_id", "provider_subscription_id"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, business_id={self.business_id}, plan={self.plan}, status={self.status})>"