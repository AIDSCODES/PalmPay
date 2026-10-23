"""Authentication API endpoints"""
from datetime import datetime
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Request, status, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.user import User, UserStatus
from app.db.models.wallet import Wallet, WalletStatus
from app.db.models.business import Business, BusinessStatus
from app.schemas.auth import LoginRequest, RegisterRequest, LoginResponse, UserAuthResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_request_id,
)
from app.core.exceptions import AuthenticationError, ConflictError, ValidationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User sign-in"
)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
):
    """
    Authenticate user via email/phone and password.
    If the merchant account is not yet provisioned, seamlessly registers
    and initializes their wallet and merchant business profile.
    """
    email_clean = login_data.email.strip().lower()
    
    # Check if user exists by email or phone
    stmt = select(User).where(
        (func.lower(User.email) == email_clean) | (User.phone == login_data.email.strip())
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Existing user: verify password if hash exists, or set password if first login
        if user.password_hash:
            if not verify_password(login_data.password, user.password_hash):
                raise AuthenticationError("Invalid email or password")
        else:
            # First password login for previously enrolled biometric user
            user.password_hash = hash_password(login_data.password)
            if not user.email and "@" in email_clean:
                user.email = email_clean
            await db.flush()
    else:
        # Create merchant user account
        name = email_clean.split("@")[0].replace(".", " ").title() if "@" in email_clean else "Merchant"
        user = User(
            name=name,
            email=email_clean if "@" in email_clean else None,
            phone=login_data.email.strip() if "@" not in email_clean else None,
            password_hash=hash_password(login_data.password),
            status=UserStatus.ACTIVE,
            email_verified=True if "@" in email_clean else False,
        )
        db.add(user)
        await db.flush()

        # Initialize wallet
        wallet = Wallet(
            user_id=user.id,
            balance=0.0,
            currency="INR",
            status=WalletStatus.ACTIVE
        )
        db.add(wallet)

        # Initialize merchant business
        business = Business(
            name=f"{name}'s Store",
            owner_id=user.id,
            status=BusinessStatus.ACTIVE,
            verification_status="verified",
            contact_email=user.email,
            contact_phone=user.phone,
        )
        db.add(business)
        await db.flush()

    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Generate JWT token
    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": "merchant_owner"
    })

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserAuthResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            status=user.status,
            role="merchant_owner",
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    )


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Direct merchant sign-up"
)
async def register(
    request: Request,
    reg_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
):
    """Register a new merchant account with email and password"""
    email_clean = reg_data.email.strip().lower()

    # Check for existing email
    stmt = select(User).where(func.lower(User.email) == email_clean)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    # Check for duplicate phone
    if reg_data.phone:
        phone_stmt = select(User).where(User.phone == reg_data.phone.strip())
        phone_res = await db.execute(phone_stmt)
        if phone_res.scalar_one_or_none():
            raise ConflictError("Phone number already registered")

    user = User(
        name=reg_data.name.strip(),
        email=email_clean,
        phone=reg_data.phone.strip() if reg_data.phone else None,
        password_hash=hash_password(reg_data.password),
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    db.add(user)
    await db.flush()

    # Wallet
    wallet = Wallet(user_id=user.id, balance=0.0, currency="INR", status=WalletStatus.ACTIVE)
    db.add(wallet)

    # Business
    business = Business(
        name=f"{user.name}'s Store",
        owner_id=user.id,
        status=BusinessStatus.ACTIVE,
        verification_status="verified",
        contact_email=user.email,
        contact_phone=user.phone,
    )
    db.add(business)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": "merchant_owner"
    })

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserAuthResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            status=user.status,
            role="merchant_owner",
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    )


@router.get(
    "/me",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current session user"
)
async def get_me(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve profile of the currently signed-in user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Authorization token required")

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
        raise NotFoundError("User not found")

    return UserAuthResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status,
        role="merchant_owner",
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User sign-out"
)
async def logout():
    """Logout endpoint"""
    return {"success": True, "message": "Successfully signed out"}
