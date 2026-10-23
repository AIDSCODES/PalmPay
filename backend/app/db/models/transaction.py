"""Transaction model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from decimal import Decimal
from sqlalchemy import String, DateTime, Enum, ForeignKey, Numeric, Index, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class TransactionType(str, PyEnum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    TOPUP = "TOPUP"


class TransactionStatus(str, PyEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    payment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")
    merchant: Mapped["User | None"] = relationship("User", foreign_keys=[merchant_id])
    payment_request: Mapped["PaymentRequest | None"] = relationship("PaymentRequest", back_populates="transaction", foreign_keys=[payment_request_id])

    __table_args__ = (
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_type", "transaction_type"),
        Index("ix_transactions_created_at", "created_at"),
        UniqueConstraint("transaction_reference", name="uq_transaction_reference"),
        UniqueConstraint("idempotency_key", "user_id", name="uq_idempotency_key_user"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, ref={self.transaction_reference}, amount={self.amount}, status={self.status})>"