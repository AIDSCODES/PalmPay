"""Business and branch models"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class BusinessStatus(str, PyEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[BusinessStatus] = mapped_column(
        Enum(BusinessStatus),
        default=BusinessStatus.PENDING,
        nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="unverified",
        nullable=False
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
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
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    branches: Mapped[list["Branch"]] = relationship(
        "Branch",
        back_populates="business",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    staff: Mapped[list["BusinessStaff"]] = relationship(
        "BusinessStaff",
        back_populates="business",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    devices: Mapped[list["PaymentDevice"]] = relationship(
        "PaymentDevice",
        back_populates="business",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    payment_requests: Mapped[list["PaymentRequest"]] = relationship(
        "PaymentRequest",
        back_populates="business",
        lazy="selectin"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="business",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="business",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_businesses_status", "status"),
        Index("ix_businesses_owner_id", "owner_id"),
        Index("ix_businesses_verification_status", "verification_status"),
    )

    def __repr__(self) -> str:
        return f"<Business(id={self.id}, name={self.name}, status={self.status})>"


class BranchStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[BranchStatus] = mapped_column(
        Enum(BranchStatus),
        default=BranchStatus.ACTIVE,
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
    business: Mapped["Business"] = relationship("Business", back_populates="branches")
    devices: Mapped[list["PaymentDevice"]] = relationship(
        "PaymentDevice",
        back_populates="branch",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    payment_requests: Mapped[list["PaymentRequest"]] = relationship(
        "PaymentRequest",
        back_populates="branch",
        lazy="selectin"
    )
    staff: Mapped[list["BusinessStaff"]] = relationship(
        "BusinessStaff",
        back_populates="branch",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_branches_business_id", "business_id"),
        Index("ix_branches_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Branch(id={self.id}, name={self.name}, business_id={self.business_id})>"