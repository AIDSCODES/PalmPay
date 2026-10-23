"""Payment request API endpoints"""
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.payment_request_service import PaymentRequestService
from app.services.audit_service import AuditService
from app.schemas.payment_request import (
    PaymentRequestCreate, PaymentRequestUpdate, PaymentRequestResponse, PaymentRequestListResponse
)
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, PaymentError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_payment_request_service(db: AsyncSession = Depends(get_db)) -> PaymentRequestService:
    return PaymentRequestService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/payment-requests",
    response_model="PaymentRequestResponse",
    status_code=status.HTTP_201_CREATED,
    tags=["Payment Requests"]
)
async def create_payment_request(
    request: Request,
    payment_data: "PaymentRequestCreate",
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id: str = Depends(get_request_id)
):
    """
    Create a new payment request.
    Merchant creates a payment request for a specific device/branch.
    """
    # Get current user from auth (placeholder)
    created_by = UUID("00000000-0000-0000-0000-000000000001")

    payment_request = await payment_service.create_payment_request(payment_data, created_by)

    await audit_service.log_event(
        "payment_request_created",
        request_id,
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        device_id=payment_request.device_id,
        metadata={"request_reference": payment_request.request_reference, "amount": float(payment_request.amount)}
    )

    from app.schemas.payment_request import PaymentRequestResponse
    return PaymentRequestResponse.model_validate(payment_request)


@router.get("/payment-requests", response_model="PaymentRequestListResponse", tags=["Payment Requests"])
async def list_payment_requests(
    request: Request,
    business_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    request_id: str = Depends(get_request_id)
):
    """List payment requests for a business"""
    requests_list, total = await payment_service.list_payment_requests(
        business_id, page, page_size, branch_id, status, start_date, end_date
    )

    from app.schemas.payment_request import PaymentRequestListResponse
    return PaymentRequestListResponse(
        payment_requests=requests_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/payment-requests/{request_id}", response_model="PaymentRequestResponse", tags=["Payment Requests"])
async def get_payment_request(
    request_id: UUID,
    request: Request,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    request_id_str: str = Depends(get_request_id)
):
    """Get payment request by ID"""
    payment_request = await payment_service.get_payment_request(request_id)
    if not payment_request:
        raise NotFoundError("Payment request not found")
    return PaymentRequestResponse.model_validate(payment_request)


@router.post(
    "/payment-requests/{request_id}/send",
    response_model="PaymentRequestResponse",
    tags=["Payment Requests"]
)
async def send_payment_request_to_device(
    request_id: UUID,
    request: Request,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id_str: str = Depends(get_request_id)
):
    """Send payment request to device"""
    payment_request = await payment_service.send_to_device(request_id)

    await audit_service.log_event(
        "payment_request_sent",
        request_id_str,
        device_id=payment_request.device_id,
        metadata={"request_reference": payment_request.request_reference}
    )

    return PaymentRequestResponse.model_validate(payment_request)


@router.post(
    "/payment-requests/{request_id}/cancel",
    response_model="PaymentRequestResponse",
    tags=["Payment Requests"]
)
async def cancel_payment_request(
    request_id: UUID,
    request: Request,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id_str: str = Depends(get_request_id)
):
    """Cancel a payment request"""
    cancelled_by = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder

    payment_request = await payment_service.cancel_payment_request(request_id, cancelled_by)

    await audit_service.log_event(
        "payment_request_cancelled",
        request_id_str,
        device_id=payment_request.device_id,
        metadata={"request_reference": payment_request.request_reference}
    )

    return PaymentRequestResponse.model_validate(payment_request)


@router.post(
    "/devices/{device_id}/acknowledge/{request_id}",
    response_model="PaymentRequestResponse",
    tags=["Payment Requests"]
)
async def device_acknowledge(
    device_id: UUID,
    request_id: UUID,
    request: Request,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    request_id_str: str = Depends(get_request_id)
):
    """Device acknowledges receipt of payment request"""
    payment_request = await payment_service.device_acknowledge(request_id, device_id)
    return PaymentRequestResponse.model_validate(payment_request)


@router.post(
    "/payment-requests/{request_id}/customer-identified",
    response_model="PaymentRequestResponse",
    tags=["Payment Requests"]
)
async def customer_identified(
    request_id: UUID,
    request: Request,
    customer_user_id: UUID,
    biometric_verified: bool = True,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    audit_service: AuditService = Depends(get_audit_service),
    request_id_str: str = Depends(get_request_id)
):
    """Customer identified via biometric - start processing payment"""
    payment_request = await payment_service.customer_identified(
        request_id, customer_user_id, biometric_verified
    )

    await audit_service.log_event(
        "customer_identified",
        request_id_str,
        user_id=customer_user_id,
        device_id=payment_request.device_id,
        metadata={"request_reference": payment_request.request_reference}
    )

    return PaymentRequestResponse.model_validate(payment_request)


@router.get(
    "/payment-requests/{request_id}/status",
    tags=["Payment Requests"]
)
async def get_payment_request_status(
    request_id: UUID,
    request: Request,
    payment_service: PaymentRequestService = Depends(get_payment_request_service),
    request_id_str: str = Depends(get_request_id)
):
    """Get payment request status"""
    payment_request = await payment_service.get_payment_request(request_id)
    if not payment_request:
        raise NotFoundError("Payment request not found")

    return {
        "request_id": str(payment_request.id),
        "request_reference": payment_request.request_reference,
        "status": payment_request.status.value,
        "amount": float(payment_request.amount),
        "currency": payment_request.currency,
        "expires_at": payment_request.expires_at.isoformat() if payment_request.expires_at else None,
        "transaction_id": str(payment_request.transaction_id) if payment_request.transaction_id else None,
        "failure_reason": payment_request.failure_reason
    }