"""Payment device model with extended fields"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class DeviceType(str, PyEnum):
    ESP32 = "ESP32"
    MOBILE = "MOBILE"
    KIOSK = "KIOSK"


class PairingStatus(str, PyEnum):
    UNPAIRED = "UNPAIRED"
    PAIRED = "PAIRED"
    PENDING = "PENDING"


class ConnectionStatus(str, PyEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class PaymentDevice(Base):
    __tablename__ = "payment_devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType),
        default=DeviceType.ESP32,
        nullable=False
    )
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Business assignment
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True
    )

    # Device credentials (hashed)
    device_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Pairing status
    pairing_status: Mapped[PairingStatus] = mapped_column(
        Enum(PairingStatus),
        default=PairingStatus.UNPAIRED,
        nullable=False
    )
    paired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    paired_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Connection status
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus),
        default=ConnectionStatus.OFFLINE,
        nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Device metadata
    device_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

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
    business: Mapped["Business"] = relationship("Business", back_populates="devices")
    branch: Mapped["Branch | None"] = relationship("Branch", back_populates="devices")
    payment_requests: Mapped[list["PaymentRequest"]] = relationship(
        "PaymentRequest",
        back_populates="device",
        lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="device",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_payment_devices_business_id", "business_id"),
        Index("ix_payment_devices_branch_id", "branch_id"),
        Index("ix_payment_devices_pairing_status", "pairing_status"),
        Index("ix_payment_devices_connection_status", "connection_status"),
        Index("ix_payment_devices_device_key_hash", "device_key_hash", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PaymentDevice(id={self.id}, name={self.device_name}, business_id={self.business_id}, pairing={self.pairing_status})>"