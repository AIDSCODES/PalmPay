"""Audit logging service"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditLog
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Audit logging service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: str,
        request_id: str,
        user_id: Optional[UUID] = None,
        device_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log an audit event"""
        # Ensure metadata doesn't contain sensitive data
        safe_metadata = metadata or {}
        # Remove any biometric data if accidentally included
        safe_metadata = {
            k: v for k, v in safe_metadata.items()
            if k not in ("embedding", "image", "biometric", "template")
        }

        audit_log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            device_id=device_id,
            request_id=request_id,
            audit_metadata=safe_metadata
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    async def log_user_event(
        self,
        event_type: str,
        user_id: UUID,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log user-related event"""
        return await self.log_event(event_type, request_id, user_id=user_id, metadata=metadata)

    async def log_device_event(
        self,
        event_type: str,
        device_id: UUID,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log device-related event"""
        return await self.log_event(event_type, request_id, device_id=device_id, metadata=metadata)

    async def log_biometric_event(
        self,
        event_type: str,
        request_id: str,
        user_id: Optional[UUID] = None,
        device_id: Optional[UUID] = None,
        matched: bool = False,
        similarity: Optional[float] = None
    ) -> AuditLog:
        """Log biometric event"""
        metadata = {
            "matched": matched,
        }
        if similarity is not None:
            metadata["similarity"] = similarity
        return await self.log_event(event_type, request_id, user_id, device_id, metadata)

    async def log_payment_event(
        self,
        event_type: str,
        request_id: str,
        user_id: UUID,
        device_id: Optional[UUID] = None,
        transaction_id: Optional[UUID] = None,
        amount: Optional[float] = None,
        status: str = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log payment event"""
        meta = {}
        if transaction_id:
            meta["transaction_id"] = str(transaction_id)
        if amount is not None:
            meta["amount"] = amount
        if status:
            meta["status"] = status
        if metadata:
            meta.update(metadata)
        return await self.log_event(event_type, request_id, user_id, device_id, meta)