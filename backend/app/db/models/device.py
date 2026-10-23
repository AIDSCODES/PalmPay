"""Device model"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Enum, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class DeviceStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    PENDING = "PENDING"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus),
        default=DeviceStatus.PENDING,
        nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    device_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

    # Relationships
    # No audit_logs relationship - audit_logs references payment_devices table

    __table_args__ = (
        Index("ix_devices_status", "status"),
        Index("ix_devices_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name={self.device_name}, status={self.status})>"