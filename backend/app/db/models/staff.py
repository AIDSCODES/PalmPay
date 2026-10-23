"""Business staff/cashier models"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class StaffRole(str, PyEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"
    VIEWER = "VIEWER"


class StaffStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REVOKED = "REVOKED"


class BusinessStaff(Base):
    __tablename__ = "business_staff"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole),
        default=StaffRole.CASHIER,
        nullable=False
    )
    status: Mapped[StaffStatus] = mapped_column(
        Enum(StaffStatus),
        default=StaffStatus.ACTIVE,
        nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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
    business: Mapped["Business"] = relationship("Business", back_populates="staff")
    branch: Mapped["Branch | None"] = relationship("Branch", back_populates="staff")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    inviter: Mapped["User | None"] = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("ix_business_staff_business_id", "business_id"),
        Index("ix_business_staff_user_id", "user_id"),
        Index("ix_business_staff_branch_id", "branch_id"),
        Index("ix_business_staff_status", "status"),
        UniqueConstraint("business_id", "user_id", name="uq_business_staff_user"),
    )

    def __repr__(self) -> str:
        return f"<BusinessStaff(id={self.id}, business_id={self.business_id}, user_id={self.user_id}, role={self.role})>"