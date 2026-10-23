"""Wallet model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from decimal import Decimal
from sqlalchemy import String, DateTime, Enum, ForeignKey, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class WalletStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        default=Decimal("0.00"),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[WalletStatus] = mapped_column(
        Enum(WalletStatus),
        default=WalletStatus.ACTIVE,
        nullable=False
    )
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
    user: Mapped["User"] = relationship("User", back_populates="wallet")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="wallet",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_wallets_status", "status"),
        UniqueConstraint("user_id", name="uq_wallet_user"),
    )

    def __repr__(self) -> str:
        return f"<Wallet(id={self.id}, user_id={self.user_id}, balance={self.balance}, currency={self.currency})>"