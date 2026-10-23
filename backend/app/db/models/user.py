"""User model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class UserStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False
    )
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    biometric_templates: Mapped[list["BiometricTemplate"]] = relationship(
        "BiometricTemplate",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    wallet: Mapped["Wallet"] = relationship(
        "Wallet",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        foreign_keys="Transaction.user_id",
        lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        lazy="selectin"
    )
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        "ConsentRecord",
        back_populates="user",
        foreign_keys="ConsentRecord.user_id",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    owned_businesses: Mapped[list["Business"]] = relationship(
        "Business",
        back_populates="owner",
        lazy="selectin"
    )
    staff_memberships: Mapped[list["BusinessStaff"]] = relationship(
        "BusinessStaff",
        back_populates="user",
        foreign_keys="BusinessStaff.user_id",
        lazy="selectin"
    )
    created_payment_requests: Mapped[list["PaymentRequest"]] = relationship(
        "PaymentRequest",
        foreign_keys="PaymentRequest.created_by",
        lazy="selectin"
    )
    customer_payment_requests: Mapped[list["PaymentRequest"]] = relationship(
        "PaymentRequest",
        foreign_keys="PaymentRequest.customer_user_id",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, status={self.status})>"