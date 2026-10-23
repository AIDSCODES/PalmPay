"""Consent record service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.consent import ConsentRecord, ConsentType, ConsentStatus
from app.schemas.consent import ConsentRecordCreate, ConsentRecordUpdate, ConsentRevokeRequest
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError, ConflictError

logger = get_logger(__name__)


class ConsentService:
    """Consent record management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_consent(self, request: ConsentRecordCreate) -> "ConsentRecord":
        """Record a new consent"""
        # Check if consent already exists for this user/type
        existing = await self.get_active_consent(request.user_id, request.consent_type)
        if existing:
            raise ConflictError("Consent already exists for this type")

        consent = ConsentRecord(
            user_id=request.user_id,
            consent_type=request.consent_type,
            policy_version=request.policy_version,
            status=ConsentStatus.GIVEN,
            policy_content=request.policy_content,
            consent_metadata=request.consent_metadata or {}
        )
        if request.expires_at:
            consent.expires_at = request.expires_at

        self.db.add(consent)
        await self.db.flush()
        return consent

    async def get_consent(self, consent_id: UUID) -> Optional["ConsentRecord"]:
        stmt = select(ConsentRecord).where(ConsentRecord.id == consent_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_consent(self, user_id: UUID, consent_type: str) -> Optional["ConsentRecord"]:
        stmt = select(ConsentRecord).where(
            ConsentRecord.user_id == UUID(request.user_id) if isinstance(request, UUID) else UUID(user_id),
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.status == "GIVEN"
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_consents(self, user_id: UUID) -> List["ConsentRecord"]:
        stmt = select(ConsentRecord).where(ConsentRecord.user_id == UUID(user_id) if isinstance(user_id, str) else user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_consent(self, consent_id: UUID, update: "ConsentRecordUpdate") -> "ConsentRecord":
        consent = await self.get_consent(consent_id)
        if not consent:
            raise NotFoundError("Consent record not found")

        if update.status is not None:
            consent.status = ConsentStatus(update.status)
            if update.status == "WITHDRAWN":
                consent.revoked_at = datetime.utcnow()
                if hasattr(request, 'user_id'):
                    consent.revoked_by = UUID(request.user_id)
                if hasattr(request, 'revocation_reason'):
                    consent.revocation_reason = request.revocation_reason

        await self.db.flush()
        return consent

    async def revoke_consent(self, user_id: UUID, consent_type: str, reason: Optional[str] = None) -> "ConsentRecord":
        """Revoke a specific consent"""
        consent = await self.get_active_consent(user_id, consent_type)
        if not consent:
            raise NotFoundError("Active consent not found")

        consent.status = ConsentStatus.WITHDRAWN
        consent.revoked_at = datetime.utcnow()
        consent.revocation_reason = reason
        await self.db.flush()

        return consent

    async def revoke_all_consents(self, user_id: UUID, reason: Optional[str] = None) -> int:
        """Revoke all active consents for a user"""
        consents = await self.get_user_consents(user_id)
        count = 0
        for consent in consents:
            if consent.status == "GIVEN":
                consent.status = ConsentStatus.WITHDRAWN
                consent.revoked_at = datetime.utcnow()
                consent.revocation_reason = reason
                count += 1

        await self.db.flush()
        return count

    async def check_consent(self, user_id: UUID, consent_type: str) -> bool:
        """Check if user has given consent"""
        consent = await self.get_active_consent(user_id, consent_type)
        if not consent:
            return False

        # Check expiry
        if consent.expires_at and consent.expires_at < datetime.utcnow():
            consent.status = ConsentStatus.EXPIRED
            await self.db.flush()
            return False

        return consent.status == ConsentStatus.GIVEN