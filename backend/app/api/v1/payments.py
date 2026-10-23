"""Payment API endpoints"""
from uuid import UUID
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.payment_service import PaymentService
from app.services.audit_service import AuditService
from app.api.dependencies import get_current_device
from app.schemas.transactions import PaymentRequest, PaymentResponse
from app.core.security import generate_request_id
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    WalletError,
    PaymentError,
    IdempotencyError
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Payments"]
)
async def process_payment(
    request: Request,
    payment_data: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    payment_service: PaymentService = Depends(get_payment_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id),
    device = Depends(get_current_device)
):
    """
    Process a payment from authenticated user.

    Requires Idempotency-Key header for duplicate protection.
    """
    try:
        transaction = await payment_service.process_payment(payment_data, idempotency_key)
    except (ValidationError, NotFoundError, WalletError) as e:
        await audit_service.log_payment_event(
            "payment_failed",
            request_id,
            user_id=payment_data.user_id,
            amount=float(payment_data.amount),
            status="failed",
            metadata={"error": str(e)}
        )
        raise
    except PaymentError as e:
        await audit_service.log_payment_event(
            "payment_error",
            request_id,
            user_id=payment_data.user_id,
            amount=float(payment_data.amount),
            status="error",
            metadata={"error": str(e)}
        )
        raise

    await audit_service.log_payment_event(
        "payment_success",
        request_id,
        user_id=payment_data.user_id,
        transaction_id=transaction.id,
        amount=float(payment_data.amount),
        status="success"
    )

    # Get updated wallet balance
    wallet = await payment_service.wallet_service.get_wallet(payment_data.user_id)
    remaining_balance = wallet.balance if wallet else Decimal("0")

    return PaymentResponse(
        success=True,
        transaction_id=str(transaction.id),
        transaction_reference=transaction.transaction_reference,
        amount=transaction.amount,
        remaining_balance=remaining_balance,
        message="Payment processed successfully",
        request_id=request_id
    )