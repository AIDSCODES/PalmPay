"""Biometric template model"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.database import Base


class BiometricTemplate(Base):
    __tablename__ = "biometric_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(512),  # Dimension will be configurable
        nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="biometric_templates")

    __table_args__ = (
        Index("ix_biometric_templates_model_version", "model_version"),
        Index("ix_biometric_templates_created_at", "created_at"),
        # Vector similarity index (HNSW) - created via migration
    )

    def __repr__(self) -> str:
        return f"<BiometricTemplate(id={self.id}, user_id={self.user_id}, model_version={self.model_version})>"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None