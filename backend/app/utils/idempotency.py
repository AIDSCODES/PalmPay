"""Idempotency key management"""
from typing import Optional
from uuid import UUID
import asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.transaction import Transaction
from app.core.logging import get_logger

logger = get_logger(__name__)


class IdempotencyManager:
    """Manage idempotency keys for payment requests"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create an in-memory lock for the key (for SQLite/tests)"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def _acquire_lock(self, idempotency_key: str, user_id: UUID) -> None:
        """Acquire a lock for the idempotency key + user_id combo"""
        lock_key = f"{idempotency_key}:{user_id}"
        # Check if we're using PostgreSQL (has pg_advisory_xact_lock)
        dialect_name = self.db.bind.dialect.name if self.db.bind else "sqlite"
        if dialect_name == "postgresql":
            # Use PostgreSQL advisory lock for cross-process synchronization
            pg_lock_key = hash(lock_key) % 2147483647
            await self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": pg_lock_key})
        else:
            # Use in-memory lock for SQLite/tests (single process)
            lock = self._get_lock(lock_key)
            await lock.acquire()

    async def _release_lock(self, idempotency_key: str, user_id: UUID) -> None:
        """Release the lock (only needed for in-memory locks)"""
        lock_key = f"{idempotency_key}:{user_id}"
        dialect_name = self.db.bind.dialect.name if self.db.bind else "sqlite"
        if dialect_name != "postgresql":
            lock = self._locks.get(lock_key)
            if lock and lock.locked():
                lock.release()

    async def check_and_store(
        self,
        idempotency_key: str,
        user_id: UUID,
        transaction_data: dict
    ) -> Optional[Transaction]:
        """
        Atomically check and reserve idempotency key.
        Uses PostgreSQL advisory lock for cross-process synchronization.
        Returns existing transaction if found, None if new (key reserved).
        """
        await self._acquire_lock(idempotency_key, user_id)

        try:
            # Now check inside the locked transaction
            stmt = select(Transaction).where(
                Transaction.idempotency_key == idempotency_key,
                Transaction.user_id == user_id
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return existing

            # Key is reserved for this user - return None to indicate caller should create transaction
            return None
        finally:
            await self._release_lock(idempotency_key, user_id)

    async def store_result(
        self,
        idempotency_key: str,
        transaction: Transaction
    ) -> None:
        """Store the completed transaction with idempotency key"""
        transaction.idempotency_key = idempotency_key
        await self.db.flush()

    async def cleanup_old_keys(self, hours: int = 24) -> int:
        """Clean up old idempotency keys (admin task)"""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(Transaction).where(
            Transaction.idempotency_key.isnot(None),
            Transaction.created_at < cutoff
        )
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        count = 0
        for txn in transactions:
            txn.idempotency_key = None
            count += 1

        if count > 0:
            await self.db.commit()
            logger.info(f"Cleaned up {count} old idempotency keys")

        return count