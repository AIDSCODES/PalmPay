"""Transaction service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.transaction import Transaction, TransactionType, TransactionStatus
from app.schemas.transactions import TransactionFilter
from app.core.logging import get_logger

logger = get_logger(__name__)


class TransactionService:
    """Transaction query service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_transaction(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID"""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        stmt = stmt.options(
            selectinload(Transaction.user),
            selectinload(Transaction.wallet),
            selectinload(Transaction.merchant)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_transactions(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[TransactionFilter] = None
    ) -> tuple[List[Transaction], int]:
        """Get paginated transactions for a user"""
        stmt = select(Transaction).where(Transaction.user_id == user_id)

        if filters:
            conditions = []
            if filters.start_date:
                conditions.append(Transaction.created_at >= filters.start_date)
            if filters.end_date:
                conditions.append(Transaction.created_at <= filters.end_date)
            if filters.status:
                conditions.append(Transaction.status == filters.status)
            if filters.transaction_type:
                conditions.append(Transaction.transaction_type == filters.transaction_type)
            if filters.merchant_id:
                conditions.append(Transaction.merchant_id == filters.merchant_id)

            if conditions:
                stmt = stmt.where(and_(*conditions))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        stmt = stmt.options(
            selectinload(Transaction.user),
            selectinload(Transaction.wallet),
            selectinload(Transaction.merchant)
        )

        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    async def get_merchant_transactions(
        self,
        merchant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[Transaction], int]:
        """Get transactions for a merchant"""
        stmt = select(Transaction).where(Transaction.merchant_id == merchant_id)

        if start_date:
            stmt = stmt.where(Transaction.created_at >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.created_at <= end_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    async def get_recent_transactions(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Transaction]:
        """Get recent transactions for a user"""
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        stmt = stmt.order_by(Transaction.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())