"""Wallet service"""
from typing import Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.wallet import Wallet, WalletStatus
from app.db.models.transaction import Transaction, TransactionType, TransactionStatus
from app.schemas.wallets import WalletCreate, WalletTopUpRequest
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError, WalletError

logger = get_logger(__name__)


class WalletService:
    """Wallet management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, user_id: UUID) -> Optional[Wallet]:
        """Get wallet by user ID"""
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_wallet_with_transactions(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[Optional[Wallet], list[Transaction], int]:
        """Get wallet with paginated transactions"""
        wallet = await self.get_wallet(user_id)
        if not wallet:
            return None, [], 0

        # Get transactions
        stmt = select(Transaction).where(Transaction.wallet_id == wallet.id)
        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        # Count total
        count_stmt = select(func.count(Transaction.id)).where(Transaction.wallet_id == wallet.id)
        total = await self.db.scalar(count_stmt) or 0

        return wallet, transactions, total

    async def create_wallet(
        self,
        wallet_data: Optional[WalletCreate] = None,
        user_id: Optional[UUID] = None,
        currency: Optional[str] = None
    ) -> Wallet:
        """Create a new wallet"""
        uid = wallet_data.user_id if wallet_data else user_id
        curr = (wallet_data.currency if wallet_data else currency) or "INR"
        init_bal = wallet_data.initial_balance if wallet_data else Decimal("0.00")
        if not uid:
            raise ValidationError("user_id required for wallet creation")

        # Check if wallet exists
        existing = await self.get_wallet(uid)
        if existing:
            return existing

        wallet = Wallet(
            user_id=uid,
            balance=init_bal,
            currency=curr,
            status=WalletStatus.ACTIVE
        )
        self.db.add(wallet)
        await self.db.flush()
        return wallet

    async def get_balance(self, user_id: UUID) -> Decimal:
        """Get wallet balance"""
        wallet = await self.get_wallet(user_id)
        if not wallet:
            raise NotFoundError("Wallet not found")
        return wallet.balance

    async def check_balance(self, user_id: UUID, amount: Decimal) -> bool:
        """Check if wallet has sufficient balance"""
        wallet = await self.get_wallet(user_id)
        if not wallet:
            return False
        return wallet.balance >= amount and wallet.status == WalletStatus.ACTIVE

    async def debit(
        self,
        user_id: UUID,
        amount: Decimal,
        transaction_id: UUID,
        description: str = None
    ) -> Wallet:
        """Debit amount from wallet (with row locking)"""
        # Use SELECT FOR UPDATE to prevent race conditions
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise NotFoundError("Wallet not found")

        if wallet.status != WalletStatus.ACTIVE:
            raise WalletError(f"Wallet is {wallet.status.value}")

        if wallet.balance < amount:
            raise WalletError("Insufficient balance")

        wallet.balance -= amount
        await self.db.flush()
        return wallet

    async def credit(
        self,
        user_id: UUID,
        amount: Decimal,
        transaction_id: UUID,
        description: str = None
    ) -> Wallet:
        """Credit amount to wallet"""
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise NotFoundError("Wallet not found")

        if wallet.status != WalletStatus.ACTIVE:
            raise WalletError(f"Wallet is {wallet.status.value}")

        wallet.balance += amount
        await self.db.flush()
        return wallet

    async def top_up(self, user_id: UUID, request: WalletTopUpRequest) -> Wallet:
        """Admin top-up wallet"""
        wallet = await self.credit(user_id, request.amount, UUID(int=0), request.description)
        return wallet

    async def freeze_wallet(self, user_id: UUID) -> Wallet:
        """Freeze wallet (admin)"""
        wallet = await self.get_wallet(user_id)
        if not wallet:
            raise NotFoundError("Wallet not found")
        wallet.status = WalletStatus.FROZEN
        await self.db.flush()
        return wallet

    async def unfreeze_wallet(self, user_id: UUID) -> Wallet:
        """Unfreeze wallet (admin)"""
        wallet = await self.get_wallet(user_id)
        if not wallet:
            raise NotFoundError("Wallet not found")
        wallet.status = WalletStatus.ACTIVE
        await self.db.flush()
        return wallet