"""API dependencies"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.payment_device_service import PaymentDeviceService
from app.db.models.payment_device import PaymentDevice
from app.core.exceptions import DeviceError, AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_current_device(
    request: Request,
    device_id: UUID = Header(..., alias="X-Device-ID"),
    device_key: str = Header(..., alias="X-Device-Key"),
    db: AsyncSession = Depends(get_db)
) -> PaymentDevice:
    """
    Dependency to authenticate device from headers.
    ESP32 must send X-Device-ID and X-Device-Key headers.
    """
    device_service = PaymentDeviceService(db)

    try:
        device = await device_service.authenticate_device(device_id, device_key)
    except DeviceError as e:
        logger.warning(f"Device authentication failed: {e.message}")
        raise AuthenticationError(e.message)

    # Store device in request state for later use
    request.state.device = device
    return device


async def get_optional_device(
    request: Request,
    device_id: Optional[UUID] = Header(None, alias="X-Device-ID"),
    device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    db: AsyncSession = Depends(get_db)
) -> Optional[PaymentDevice]:
    """Optional device authentication"""
    if not device_id or not device_key:
        return None

    device_service = PaymentDeviceService(db)
    try:
        return await device_service.authenticate_device(device_id, device_key)
    except DeviceError:
        return None


async def require_admin(
    request: Request,
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
) -> bool:
    """Require admin API key"""
    from app.core.config import settings
    if not admin_key or admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return True


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to retrieve the authenticated user from Bearer JWT"""
    from app.core.security import decode_access_token
    from app.db.models.user import User, UserStatus
    from sqlalchemy import select

    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Authorization header required")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthenticationError("Invalid or expired session token")

    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        raise AuthenticationError("Invalid user token payload")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise AuthenticationError("User not found")
    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError("User account is inactive")

    request.state.user = user
    return user


async def get_optional_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Optional user authentication"""
    try:
        return await get_current_user(request, authorization, db)
    except Exception:
        return None