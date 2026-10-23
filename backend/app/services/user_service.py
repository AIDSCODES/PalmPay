"""User service"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.user import User, UserStatus
from app.db.models.wallet import Wallet
from app.schemas.users import UserCreateInternal, UserUpdate
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, ValidationError

logger = get_logger(__name__)


class UserService:
    """User management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreateInternal) -> User:
        """Create a new user"""
        # Check for duplicate phone
        if user_data.phone:
            stmt = select(User).where(User.phone == user_data.phone)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise ConflictError("Phone number already registered")

        user = User(
            name=user_data.name,
            phone=user_data.phone,
            status=UserStatus.ACTIVE
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_with_relations(self, user_id: UUID) -> Optional[User]:
        """Get user with biometric templates and wallet"""
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.biometric_templates),
            selectinload(User.wallet)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number"""
        stmt = select(User).where(User.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Update user information"""
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        if user_data.name is not None:
            user.name = user_data.name
        if user_data.phone is not None:
            # Check for duplicate
            if user_data.phone != user.phone:
                stmt = select(User).where(User.phone == user_data.phone)
                result = await self.db.execute(stmt)
                if result.scalar_one_or_none():
                    raise ConflictError("Phone number already registered")
            user.phone = user_data.phone
        if user_data.status is not None:
            user.status = user_data.status

        await self.db.flush()
        return user

    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate (soft delete) a user"""
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        user.status = UserStatus.DELETED
        await self.db.flush()
        return user

    async def suspend_user(self, user_id: UUID) -> User:
        """Suspend a user"""
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        user.status = UserStatus.SUSPENDED
        await self.db.flush()
        return user

    async def reactivate_user(self, user_id: UUID) -> User:
        """Reactivate a suspended user"""
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        if user.status == UserStatus.DELETED:
            raise ValidationError("Cannot reactivate deleted user")

        user.status = UserStatus.ACTIVE
        await self.db.flush()
        return user

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[UserStatus] = None
    ) -> tuple[List[User], int]:
        """List users with pagination"""
        stmt = select(User)

        if status:
            stmt = stmt.where(User.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(User.created_at.desc())

        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    async def create_wallet_for_user(self, user_id: UUID, currency: str = "INR") -> Wallet:
        """Create a wallet for a user"""
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Check if wallet already exists
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError("Wallet already exists for user")

        wallet = Wallet(
            user_id=user_id,
            currency=currency,
            status=WalletStatus.ACTIVE
        )
        self.db.add(wallet)
        await self.db.flush()
        return wallet