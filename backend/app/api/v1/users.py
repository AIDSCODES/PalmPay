"""User API endpoints"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.biometric_service import BiometricService
from app.services.audit_service import AuditService
from app.schemas.users import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
    UserUpdate,
    UserListResponse,
    UserCreateInternal,
)
from app.schemas.biometric import BiometricEnrollmentRequest, BiometricEnrollmentResponse
from app.schemas.common import PaginationParams
from app.core.security import generate_request_id
from app.core.config import settings
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    BiometricError,
    ModelError
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


def get_wallet_service(db: AsyncSession = Depends(get_db)) -> WalletService:
    return WalletService(db)


def get_biometric_service(db: AsyncSession = Depends(get_db)) -> BiometricService:
    return BiometricService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


@router.post(
    "/users/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"]
)
async def register_user(
    request: Request,
    name: str = Form(...),
    phone: str = Form(None),
    samples: list[UploadFile] = File(...),
    user_service: UserService = Depends(get_user_service),
    wallet_service: WalletService = Depends(get_wallet_service),
    biometric_service: BiometricService = Depends(get_biometric_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Register a new user with palm vein biometric samples.

    ESP32 sends multipart/form-data with:
    - name: User's name
    - phone: Optional phone number
    - samples: Multiple palm image files (3-5)
    """
    # Validate sample count
    if len(samples) < 3:
        raise ValidationError("At least 3 palm samples required")
    if len(samples) > 5:
        raise ValidationError("Maximum 5 palm samples allowed")

    # Read and validate images
    image_data = []
    for sample in samples:
        content = await sample.read()
        if len(content) > settings.IMAGE_MAX_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"Image too large (max {settings.IMAGE_MAX_SIZE_MB}MB)")

        # Convert to base64
        import base64
        b64 = base64.b64encode(content).decode()
        image_data.append(b64)

    # Create user
    try:
        user_data = UserRegisterRequest(name=name, phone=phone)
        user = await user_service.create_user(
            UserCreateInternal(name=user_data.name, phone=user_data.phone)
        )
    except ConflictError as e:
        await audit_service.log_event(
            "user_registration_failed",
            request_id,
            metadata={"error": str(e), "phone": phone}
        )
        raise

    # Enroll biometric
    try:
        templates, quality_scores = await biometric_service.enroll_user(user.id, image_data)
    except (BiometricError, ValidationError, ModelError) as e:
        # Rollback user creation
        await user_service.deactivate_user(user.id)
        await audit_service.log_event(
            "user_registration_failed",
            request_id,
            user_id=user.id,
            metadata={"error": str(e), "stage": "biometric_enrollment"}
        )
        raise

    # Create wallet
    try:
        await wallet_service.create_wallet(user_id=user.id, currency=settings.DEFAULT_CURRENCY)
    except Exception as e:
        logger.error(f"Wallet creation failed for user {user.id}: {e}")
        # Don't fail registration for wallet issues

    await audit_service.log_user_event(
        "user_registered",
        user.id,
        request_id,
        metadata={"template_count": len(templates), "avg_quality": sum(quality_scores)/len(quality_scores)}
    )

    return UserRegisterResponse(
        success=True,
        user_id=user.id,
        message="User registered successfully",
        request_id=request_id
    )


@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    request_id: str = Depends(get_request_id)
):
    """Get user by ID"""
    user = await user_service.get_user(user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    request_id: str = Depends(get_request_id)
):
    """Update user information"""
    user = await user_service.update_user(user_id, user_data)
    return user