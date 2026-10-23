"""Admin API endpoints"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.user_service import UserService
from app.services.device_service import DeviceService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService
from app.services.audit_service import AuditService
from app.schemas.users import UserListResponse, UserResponse
from app.schemas.devices import DeviceListResponse, DeviceResponse
from app.schemas.transactions import TransactionResponse
from app.core.security import generate_request_id
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    return DeviceService(db)


def get_transaction_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


def get_wallet_service(db: AsyncSession = Depends(get_db)) -> WalletService:
    return WalletService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


async def verify_admin_key(request: Request, admin_key: str = Header(None, alias="X-Admin-Key")):
    """Verify admin API key"""
    if not admin_key or admin_key != settings.ADMIN_API_KEY:
        raise AuthorizationError("Invalid or missing admin API key")
    return True


@router.get("/users", response_model=UserListResponse, dependencies=[Depends(verify_admin_key)])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user_service: UserService = Depends(get_user_service),
    request_id: str = Depends(get_request_id)
):
    """List all users (admin)"""
    from app.db.models.user import UserStatus
    user_status = UserStatus(status) if status else None
    users, total = await user_service.list_users(page, page_size, user_status)
    return UserListResponse(users=users, total=total, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(verify_admin_key)])
async def get_user_admin(
    user_id: UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    request_id: str = Depends(get_request_id)
):
    """Get user details (admin)"""
    user = await user_service.get_user_with_relations(user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


@router.post("/users/{user_id}/suspend", response_model=UserResponse, dependencies=[Depends(verify_admin_key)])
async def suspend_user(
    user_id: UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Suspend a user (admin)"""
    user = await user_service.suspend_user(user_id)
    await audit_service.log_user_event("user_suspended", request_id, user_id=user_id)
    return user


@router.post("/users/{user_id}/reactivate", response_model=UserResponse, dependencies=[Depends(verify_admin_key)])
async def reactivate_user(
    user_id: UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Reactivate a suspended user (admin)"""
    user = await user_service.reactivate_user(user_id)
    await audit_service.log_user_event("user_reactivated", request_id, user_id=user_id)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserResponse, dependencies=[Depends(verify_admin_key)])
async def deactivate_user(
    user_id: UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Deactivate (soft delete) a user (admin)"""
    user = await user_service.deactivate_user(user_id)
    await audit_service.log_user_event("user_deactivated", request_id, user_id=user_id)
    return user


@router.get("/devices", response_model=DeviceListResponse, dependencies=[Depends(verify_admin_key)])
async def list_devices(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    device_service: DeviceService = Depends(get_device_service),
    request_id: str = Depends(get_request_id)
):
    """List all devices (admin)"""
    from app.db.models.device import DeviceStatus
    device_status = DeviceStatus(status) if status else None
    devices, total = await device_service.list_devices(page, page_size, device_status)
    return DeviceListResponse(devices=devices, total=total, page=page, page_size=page_size)


@router.post("/devices/{device_id}/revoke", response_model=DeviceResponse, dependencies=[Depends(verify_admin_key)])
async def revoke_device(
    device_id: UUID,
    request: Request,
    device_service: DeviceService = Depends(get_device_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Revoke a device (admin)"""
    device = await device_service.revoke_device(device_id)
    await audit_service.log_device_event("device_revoked", request_id, device_id=device_id)
    return device


@router.post("/devices/{device_id}/activate", response_model=DeviceResponse, dependencies=[Depends(verify_admin_key)])
async def activate_device(
    device_id: UUID,
    request: Request,
    device_service: DeviceService = Depends(get_device_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """Activate a pending device (admin)"""
    device = await device_service.activate_device(device_id)
    await audit_service.log_device_event("device_activated", request_id, device_id=device_id)
    return device


@router.get("/transactions", dependencies=[Depends(verify_admin_key)])
async def list_all_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    transaction_service: TransactionService = Depends(get_transaction_service),
    request_id: str = Depends(get_request_id)
):
    """List all transactions (admin) - simplified for prototype"""
    # Would implement full filtering in production
    if user_id:
        transactions, total = await transaction_service.get_user_transactions(user_id, page, page_size)
        return TransactionListResponse(transactions=transactions, total=total, page=page, page_size=page_size)
    raise ValidationError("User ID filter required for prototype")


@router.get("/model/status", dependencies=[Depends(verify_admin_key)])
async def model_status(
    request: Request,
    request_id: str = Depends(get_request_id)
):
    """Get model status (admin)"""
    from app.ml.embedding import embedding_service
    from app.ml.liveness import liveness_detector, MockLivenessDetector
    return {
        "model_version": embedding_service.model_version,
        "embedding_dim": embedding_service.embedding_dim,
        "model_type": type(embedding_service.model).__name__,
        "is_mock": isinstance(embedding_service.model, __import__('app.ml.model', fromlist=['MockPalmEmbeddingModel']).MockPalmEmbeddingModel),
        "liveness_type": type(liveness_detector).__name__,
        "is_mock_liveness": isinstance(liveness_detector, MockLivenessDetector),
        "realtime_active": True
    }