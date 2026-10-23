"""Consent records model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class ConsentType(str, PyEnum):
    BIOMETRIC_ENROLLMENT = "BIOMETRIC_ENROLLMENT"
    BIOMETRIC_IDENTIFICATION = "BIOMETRIC_IDENTIFICATION"
    DATA_PROCESSING = "DATA_PROCESSING"
    MARKETING = "MARKETING"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"


class ConsentStatus(str, PyEnum):
    GIVEN = "GIVEN"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        Enum(ConsentType),
        nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus),
        default=ConsentStatus.GIVEN,
        nullable=False
    )
    consent_given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    policy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

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
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    revoker: Mapped["User | None"] = relationship("User", foreign_keys=[revoked_by])

    __table_args__ = (
        Index("ix_consent_records_user_id", "user_id"),
        Index("ix_consent_records_consent_type", "consent_type"),
        Index("ix_consent_records_status", "status"),
        Index("ix_consent_records_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<ConsentRecord(id={self.id}, user_id={self.user_id}, type={self.consent_type}, status={self.status})>"