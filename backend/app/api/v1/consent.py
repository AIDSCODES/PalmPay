"""Consent API endpoints"""
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.consent_service import ConsentService
from app.schemas.consent import (
    ConsentRecordCreate, ConsentRecordUpdate, ConsentRecordResponse, ConsentRecordListResponse,
    ConsentRevokeRequest
)
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_consent_service(db: AsyncSession = Depends(get_db)) -> "ConsentService":
    from app.services.consent_service import ConsentService
    return ConsentService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/consents",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Consents"]
)
async def record_consent(
    request: Request,
    consent_data: ConsentRecordCreate,
    consent_service: "ConsentService" = Depends(get_consent_service),
    request_id: str = Depends(get_request_id)
):
    """Record a new consent"""
    # Get current user from auth (placeholder)
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    consent = await consent_service.record_consent(consent_data)
    return ConsentRecordResponse.model_validate(consent)


@router.get("/consents/me", response_model=ConsentRecordListResponse, tags=["Consents"])
async def get_my_consents(
    request: Request,
    consent_service: "ConsentService" = Depends(get_consent_service),
    request_id: str = Depends(get_request_id)
):
    """Get current user's consent records"""
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    consents = await consent_service.get_user_consents(user_id)
    return ConsentRecordListResponse(
        consents=[ConsentRecordResponse.model_validate(c) for c in consents],
        total=len(consents),
        page=1,
        page_size=len(consents)
    )


@router.get("/consents/me/{consent_type}", tags=["Consents"])
async def check_my_consent(
    consent_type: str,
    request: Request,
    consent_service: "ConsentService" = Depends(get_consent_service),
    request_id: str = Depends(get_request_id)
):
    """Check if current user has given a specific consent"""
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    has_consent = await consent_service.check_consent(user_id, consent_type)
    return {"has_consent": has_consent}


@router.post("/consents/revoke", tags=["Consents"])
async def revoke_consent(
    request: Request,
    revoke_data: ConsentRevokeRequest,
    consent_service: "ConsentService" = Depends(get_consent_service),
    request_id: str = Depends(get_request_id)
):
    """Revoke a specific consent"""
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    consent = await consent_service.revoke_consent(user_id, revoke_data.consent_type, revoke_data.revocation_reason)
    return {"message": "Consent revoked successfully", "consent_id": str(consent.id)}


@router.post("/consents/revoke-all", tags=["Consents"])
async def revoke_all_consents(
    request: Request,
    reason: Optional[str] = None,
    consent_service: "ConsentService" = Depends(get_consent_service),
    request_id: str = Depends(get_request_id)
):
    """Revoke all consents for current user"""
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    count = await consent_service.revoke_all_consents(user_id, reason)
    return {"message": f"Revoked {count} consents", "revoked_count": count}