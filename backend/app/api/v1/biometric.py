"""Biometric API endpoints"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.biometric_service import BiometricService
from app.services.audit_service import AuditService
from app.schemas.biometric import (
    BiometricIdentifyRequest,
    BiometricIdentifyResponse,
    BiometricEnrollmentRequest,
    BiometricEnrollmentResponse,
    BiometricQualityCheckResponse,
)
from app.schemas.common import PaginationParams
from app.core.security import generate_request_id
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    BiometricError,
    ModelError
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_biometric_service(db: AsyncSession = Depends(get_db)) -> BiometricService:
    return BiometricService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/biometric/identify",
    response_model=BiometricIdentifyResponse,
    tags=["Biometric"]
)
async def identify_user(
    request: Request,
    image: UploadFile = File(...),
    biometric_service: BiometricService = Depends(get_biometric_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Identify user from palm vein image.

    ESP32 sends a single palm image file.
    Returns matched user_id and similarity score.
    """
    # Read image
    content = await image.read()
    import base64
    b64_image = base64.b64encode(content).decode()

    try:
        matched, user_id, similarity, reason = await biometric_service.identify(b64_image)
    except (ValidationError, ModelError) as e:
        await audit_service.log_biometric_event(
            "identification_failed",
            request_id,
            device_id=None,
            matched=False,
            metadata={"error": str(e)}
        )
        raise

    await audit_service.log_biometric_event(
        "identification_attempt",
        request_id,
        user_id=user_id,
        matched=matched,
        similarity=similarity
    )

    return BiometricIdentifyResponse(
        matched=matched,
        user_id=user_id,
        similarity=similarity,
        reason=reason,
        request_id=request_id
    )


@router.post(
    "/biometric/enroll",
    response_model=BiometricEnrollmentResponse,
    tags=["Biometric"]
)
async def enroll_biometric(
    request: Request,
    user_id: UUID,
    images: list[UploadFile] = File(...),
    biometric_service: BiometricService = Depends(get_biometric_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Enroll additional biometric samples for existing user.
    """
    if len(images) < 1 or len(images) > 3:
        raise ValidationError("Provide 1-3 additional samples")

    image_data = []
    for img in images:
        content = await img.read()
        import base64
        image_data.append(base64.b64encode(content).decode())

    try:
        templates, quality_scores = await biometric_service.enroll_user(user_id, image_data)
    except (ValidationError, ModelError, BiometricError) as e:
        await audit_service.log_biometric_event(
            "enrollment_failed",
            request_id,
            user_id=user_id,
            metadata={"error": str(e)}
        )
        raise

    await audit_service.log_biometric_event(
        "enrollment_added",
        request_id,
        user_id=user_id,
        metadata={"template_count": len(templates)}
    )

    return BiometricEnrollmentResponse(
        success=True,
        user_id=user_id,
        quality_scores=quality_scores,
        message=f"Added {len(templates)} biometric templates",
        request_id=request_id
    )


@router.post(
    "/biometric/verify",
    response_model=BiometricIdentifyResponse,
    tags=["Biometric"]
)
async def verify_user(
    request: Request,
    user_id: UUID,
    image: UploadFile = File(...),
    biometric_service: BiometricService = Depends(get_biometric_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Verify a specific user (1:1 matching).
    """
    content = await image.read()
    import base64
    b64_image = base64.b64encode(content).decode()

    try:
        matched, similarity, reason = await biometric_service.verify_user(user_id, b64_image)
    except (ValidationError, ModelError) as e:
        await audit_service.log_biometric_event(
            "verification_failed",
            request_id,
            user_id=user_id,
            metadata={"error": str(e)}
        )
        raise

    await audit_service.log_biometric_event(
        "verification_attempt",
        request_id,
        user_id=user_id,
        matched=matched,
        similarity=similarity
    )

    return BiometricIdentifyResponse(
        matched=matched,
        user_id=user_id if matched else None,
        similarity=similarity,
        reason=reason,
        request_id=request_id
    )


@router.post(
    "/biometric/quality",
    response_model=BiometricQualityCheckResponse,
    tags=["Biometric"]
)
async def check_image_quality(
    request: Request,
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id)
):
    """
    Check palm image quality without identification.
    """
    from app.utils.image import image_processor

    content = await image.read()
    import base64
    b64_image = base64.b64encode(content).decode()

    try:
        decoded = image_processor.decode_base64_image(b64_image)
        quality = image_processor.assess_quality(decoded)
        is_valid, issues = image_processor.validate_image(decoded)
    except ValueError as e:
        raise ValidationError(f"Invalid image: {e}")

    return BiometricQualityCheckResponse(
        quality_score=quality,
        is_acceptable=quality >= 0.5 and is_valid,
        issues=issues
    )