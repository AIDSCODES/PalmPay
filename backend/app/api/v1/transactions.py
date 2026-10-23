"""Transaction API endpoints"""
from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.transaction_service import TransactionService
from app.schemas.transactions import TransactionResponse, TransactionFilter, TransactionListResponse
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_transaction_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.get(
    "/transactions/{user_id}",
    response_model=TransactionListResponse,
    tags=["Transactions"]
)
async def get_user_transactions(
    user_id: UUID,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_id: Optional[UUID] = None,
    transaction_service: TransactionService = Depends(get_transaction_service),
    request_id: str = Depends(get_request_id)
):
    """Get paginated transaction history for a user"""
    from app.db.models.transaction import TransactionStatus, TransactionType

    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        status=TransactionStatus(status) if status else None,
        transaction_type=TransactionType(transaction_type) if transaction_type else None,
        merchant_id=merchant_id
    )

    transactions, total = await transaction_service.get_user_transactions(
        user_id, page, page_size, filters
    )

    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/transactions/detail/{transaction_id}",
    response_model=TransactionResponse,
    tags=["Transactions"]
)
async def get_transaction(
    transaction_id: UUID,
    request: Request,
    transaction_service: TransactionService = Depends(get_transaction_service),
    request_id: str = Depends(get_request_id)
):
    """Get transaction details by ID"""
    transaction = await transaction_service.get_transaction(transaction_id)
    if not transaction:
        raise NotFoundError("Transaction not found")
    return transaction