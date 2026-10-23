"""Wallet API endpoints"""
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.wallet_service import WalletService
from app.services.audit_service import AuditService
from app.schemas.wallets import WalletResponse, WalletBalanceResponse, WalletTopUpRequest
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_wallet_service(db: AsyncSession = Depends(get_db)) -> WalletService:
    return WalletService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.get("/wallets/{user_id}", response_model=WalletBalanceResponse, tags=["Wallets"])
async def get_wallet(
    user_id: UUID,
    request: Request,
    wallet_service: WalletService = Depends(get_wallet_service),
    request_id: str = Depends(get_request_id)
):
    """Get wallet balance for a user"""
    wallet = await wallet_service.get_wallet(user_id)
    if not wallet:
        raise NotFoundError("Wallet not found")

    return WalletBalanceResponse(
        user_id=user_id,
        balance=wallet.balance,
        currency=wallet.currency,
        status=wallet.status
    )


@router.post("/wallets/{user_id}/topup", response_model=WalletResponse, tags=["Wallets", "Admin"])
async def topup_wallet(
    user_id: UUID,
    request: Request,
    topup_data: WalletTopUpRequest,
    wallet_service: WalletService = Depends(get_wallet_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Top up wallet (admin only).
    In production, this should be protected by admin authentication.
    """
    wallet = await wallet_service.top_up(user_id, topup_data)

    await audit_service.log_event(
        "wallet_topup",
        request_id,
        user_id=user_id,
        metadata={"amount": float(topup_data.amount), "description": topup_data.description}
    )

    return wallet