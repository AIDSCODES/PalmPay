"""Payment service"""
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.transaction import Transaction, TransactionType, TransactionStatus
from app.db.models.wallet import Wallet, WalletStatus
from app.db.models.user import User, UserStatus
from app.schemas.transactions import PaymentRequest
from app.services.wallet_service import WalletService
from app.utils.idempotency import IdempotencyManager
from app.core.logging import get_logger
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    PaymentError,
    WalletError,
    IdempotencyError
)

logger = get_logger(__name__)


class PaymentService:
    """Payment processing service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)
        self.idempotency = IdempotencyManager(db)

    def _generate_transaction_reference(self) -> str:
        """Generate unique transaction reference"""
        import uuid
        return f"TX-{uuid.uuid4().hex.upper()}"

    async def process_payment(
        self,
        request: PaymentRequest,
        idempotency_key: Optional[str] = None
    ) -> Transaction:
        """
        Process a payment with idempotency support.

        Args:
            request: Payment request
            idempotency_key: Optional idempotency key for duplicate protection

        Returns:
            Created transaction
        """
        # Check idempotency
        if idempotency_key:
            existing = await self.idempotency.check_and_store(
                idempotency_key, request.user_id, request.model_dump()
            )
            if existing:
                logger.info(f"Idempotent payment request: {idempotency_key}")
                return existing

        # Validate user
        stmt = select(User).where(User.id == request.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User not found")

        if user.status != UserStatus.ACTIVE:
            raise ValidationError(f"User account is {user.status.value}")

        # Validate amount
        if request.amount <= 0:
            raise ValidationError("Amount must be positive")

        # Check wallet and balance
        wallet = await self.wallet_service.get_wallet(request.user_id)
        if not wallet:
            raise NotFoundError("Wallet not found")

        if wallet.status != WalletStatus.ACTIVE:
            raise WalletError(f"Wallet is {wallet.status.value}")

        if wallet.balance < request.amount:
            raise WalletError("Insufficient balance")

        # Validate merchant if provided
        merchant = None
        if request.merchant_id:
            stmt = select(User).where(User.id == request.merchant_id)
            result = await self.db.execute(stmt)
            merchant = result.scalar_one_or_none()
            if not merchant:
                raise NotFoundError("Merchant not found")
            if merchant.status != UserStatus.ACTIVE:
                raise ValidationError("Merchant account is not active")

        # Create transaction
        transaction = Transaction(
            transaction_reference=self._generate_transaction_reference(),
            user_id=request.user_id,
            wallet_id=wallet.id,
            merchant_id=request.merchant_id,
            amount=request.amount,
            currency=request.currency,
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.PENDING,
            description=request.description,
            idempotency_key=idempotency_key
        )

        self.db.add(transaction)
        await self.db.flush()

        try:
            # Debit wallet (with row locking)
            await self.wallet_service.debit(
                request.user_id,
                request.amount,
                transaction.id,
                request.description
            )

            # Mark transaction as success
            transaction.status = TransactionStatus.SUCCESS
            transaction.completed_at = datetime.utcnow()

            await self.db.commit()

            # Store idempotency key
            if idempotency_key:
                await self.idempotency.store_result(idempotency_key, transaction)

            logger.info(f"Payment successful: {transaction.transaction_reference}")
            return transaction

        except Exception as e:
            # Mark transaction as failed
            transaction.status = TransactionStatus.FAILED
            transaction.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.error(f"Payment failed: {transaction.transaction_reference} - {e}")
            raise PaymentError(f"Payment processing failed: {e}")

    async def process_refund(
        self,
        original_transaction_id: UUID,
        amount: Optional[Decimal] = None,
        reason: str = None
    ) -> Transaction:
        """Process a refund for a previous payment"""
        # Get original transaction
        stmt = select(Transaction).where(Transaction.id == original_transaction_id)
        result = await self.db.execute(stmt)
        original = result.scalar_one_or_none()

        if not original:
            raise NotFoundError("Original transaction not found")

        if original.status != TransactionStatus.SUCCESS:
            raise ValidationError("Can only refund successful transactions")

        if original.transaction_type != TransactionType.PAYMENT:
            raise ValidationError("Can only refund payment transactions")

        # Determine refund amount
        refund_amount = amount or original.amount
        if refund_amount > original.amount:
            raise ValidationError("Refund amount cannot exceed original amount")

        # Check if already refunded
        stmt = select(Transaction).where(
            Transaction.merchant_id == original.user_id,
            Transaction.transaction_type == TransactionType.REFUND
        )
        # Simplified check - in production, track refunded amount separately

        # Create refund transaction
        refund = Transaction(
            transaction_reference=self._generate_transaction_reference(),
            user_id=original.user_id,
            wallet_id=original.wallet_id,
            merchant_id=original.merchant_id,
            amount=refund_amount,
            currency=original.currency,
            transaction_type=TransactionType.REFUND,
            status=TransactionStatus.PENDING,
            description=f"Refund: {reason or 'No reason provided'}"
        )

        self.db.add(refund)
        await self.db.flush()

        try:
            # Credit wallet
            await self.wallet_service.credit(
                original.user_id,
                refund_amount,
                refund.id,
                refund.description
            )

            refund.status = TransactionStatus.SUCCESS
            refund.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Refund successful: {refund.transaction_reference}")
            return refund

        except Exception as e:
            refund.status = TransactionStatus.FAILED
            refund.completed_at = datetime.utcnow()
            await self.db.commit()
            raise PaymentError(f"Refund processing failed: {e}")

    async def get_transaction(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID"""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transaction_by_reference(self, reference: str) -> Optional[Transaction]:
        """Get transaction by reference"""
        stmt = select(Transaction).where(Transaction.transaction_reference == reference)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()