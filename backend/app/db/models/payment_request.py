"""Payment request model with state machine"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Numeric, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class PaymentRequestStatus(str, PyEnum):
    CREATED = "CREATED"
    SENT_TO_DEVICE = "SENT_TO_DEVICE"
    AWAITING_CUSTOMER = "AWAITING_CUSTOMER"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    # Business hierarchy
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_devices.id", ondelete="SET NULL"),
        nullable=True
    )

    # Created by
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )

    # Payment details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # State machine
    status: Mapped[PaymentRequestStatus] = mapped_column(
        Enum(PaymentRequestStatus),
        default=PaymentRequestStatus.CREATED,
        nullable=False
    )

    # Idempotency
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Device communication
    sent_to_device_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    device_acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Customer interaction
    customer_identified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    customer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Processing
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    # Result
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

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
    business: Mapped["Business"] = relationship("Business", back_populates="payment_requests")
    branch: Mapped["Branch | None"] = relationship("Branch", back_populates="payment_requests")
    device: Mapped["PaymentDevice | None"] = relationship("PaymentDevice", back_populates="payment_requests")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    customer: Mapped["User | None"] = relationship("User", foreign_keys=[customer_user_id])
    transaction: Mapped["Transaction | None"] = relationship("Transaction", foreign_keys=[transaction_id])
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="payment_request",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_payment_requests_business_id", "business_id"),
        Index("ix_payment_requests_branch_id", "branch_id"),
        Index("ix_payment_requests_device_id", "device_id"),
        Index("ix_payment_requests_created_by", "created_by"),
        Index("ix_payment_requests_status", "status"),
        Index("ix_payment_requests_expires_at", "expires_at"),
        Index("ix_payment_requests_customer_user_id", "customer_user_id"),
        Index("ix_payment_requests_transaction_id", "transaction_id"),
        Index("ix_payment_requests_idempotency_key", "idempotency_key", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PaymentRequest(id={self.id}, ref={self.request_reference}, status={self.status}, amount={self.amount})>"

    def can_transition_to(self, new_status: "PaymentRequestStatus") -> bool:
        """Check if state transition is valid"""
        valid_transitions = {
            PaymentRequestStatus.CREATED: [PaymentRequestStatus.SENT_TO_DEVICE, PaymentRequestStatus.CANCELLED, PaymentRequestStatus.EXPIRED],
            PaymentRequestStatus.SENT_TO_DEVICE: [PaymentRequestStatus.AWAITING_CUSTOMER, PaymentRequestStatus.CANCELLED, PaymentRequestStatus.EXPIRED],
            PaymentRequestStatus.AWAITING_CUSTOMER: [PaymentRequestStatus.PROCESSING, PaymentRequestStatus.CANCELLED, PaymentRequestStatus.EXPIRED],
            PaymentRequestStatus.PROCESSING: [PaymentRequestStatus.SUCCEEDED, PaymentRequestStatus.FAILED],
            PaymentRequestStatus.SUCCEEDED: [],
            PaymentRequestStatus.FAILED: [],
            PaymentRequestStatus.CANCELLED: [],
            PaymentRequestStatus.EXPIRED: [],
        }
        return new_status in valid_transitions.get(self.status, [])