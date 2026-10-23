"""Audit log model"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_devices.id", ondelete="SET NULL"),
        nullable=True
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True
    )
    payment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_requests.id", ondelete="SET NULL"),
        nullable=True
    )
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    audit_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    device: Mapped[Optional["PaymentDevice"]] = relationship("PaymentDevice", back_populates="audit_logs")
    business: Mapped[Optional["Business"]] = relationship("Business", back_populates="audit_logs")
    payment_request: Mapped[Optional["PaymentRequest"]] = relationship("PaymentRequest", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_device_id", "device_id"),
        Index("ix_audit_logs_business_id", "business_id"),
        Index("ix_audit_logs_payment_request_id", "payment_request_id"),
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, request_id={self.request_id})>"