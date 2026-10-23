"""Business staff service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.staff import BusinessStaff, StaffRole, StaffStatus
from app.db.models.business import Business, Branch
from app.db.models.user import User
from app.schemas.staff import BusinessStaffCreate, BusinessStaffUpdate
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, ValidationError

logger = get_logger(__name__)


class StaffService:
    """Business staff management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def invite_staff(
        self,
        business_id: UUID,
        request: BusinessStaffCreate,
        invited_by: UUID
    ) -> BusinessStaff:
        """Invite a staff member to a business"""
        # Verify business exists
        business = await self._get_business(business_id)
        if not business:
            raise NotFoundError("Business not found")

        # Verify branch if provided
        if request.branch_id:
            branch = await self._get_branch(request.branch_id, business_id)
            if not branch:
                raise NotFoundError("Branch not found")

        # Verify user exists
        user = await self._get_user(request.user_id)
        if not user:
            raise NotFoundError("User not found")

        # Check if already a staff member
        existing = await self.get_staff_by_user(business_id, request.user_id)
        if existing:
            raise ConflictError("User is already a staff member of this business")

        staff = BusinessStaff(
            business_id=business_id,
            branch_id=request.branch_id,
            user_id=request.user_id,
            role=request.role,
            status=StaffStatus.ACTIVE,
            invited_by=invited_by,
            joined_at=datetime.utcnow()
        )
        self.db.add(staff)
        await self.db.flush()
        return staff

    async def get_staff(self, staff_id: UUID) -> Optional["BusinessStaff"]:
        """Get staff by ID"""
        stmt = select(BusinessStaff).where(BusinessStaff.id == staff_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_staff_by_user(self, business_id: UUID, user_id: UUID) -> Optional["BusinessStaff"]:
        """Get staff by user ID within a business"""
        stmt = select(BusinessStaff).where(
            BusinessStaff.business_id == business_id,
            BusinessStaff.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_staff_for_branch(self, branch_id: UUID) -> List["BusinessStaff"]:
        """Get all staff for a branch"""
        stmt = select(BusinessStaff).where(BusinessStaff.branch_id == branch_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_staff(
        self,
        business_id: UUID,
        page: int = 1,
        page_size: int = 20,
        branch_id: Optional[UUID] = None,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> tuple[List["BusinessStaff"], int]:
        """List staff with pagination"""
        from app.db.models.staff import StaffStatus, StaffRole

        stmt = select(BusinessStaff).where(BusinessStaff.business_id == business_id)

        if branch_id:
            stmt = stmt.where(BusinessStaff.branch_id == branch_id)
        if status:
            stmt = stmt.where(BusinessStaff.status == StaffStatus(status))
        if role:
            stmt = stmt.where(BusinessStaff.role == StaffRole(role))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(BusinessStaff.created_at.desc())

        result = await self.db.execute(stmt)
        staff = list(result.scalars().all())

        return staff, total

    async def update_staff(self, staff_id: UUID, update: BusinessStaffUpdate) -> "BusinessStaff":
        """Update staff information"""
        staff = await self.get_staff(staff_id)
        if not staff:
            raise NotFoundError("Staff member not found")

        if update.branch_id is not None:
            if update.branch_id:
                branch = await self._get_branch(update.branch_id, staff.business_id)
                if not branch:
                    raise NotFoundError("Branch not found")
            staff.branch_id = update.branch_id

        if update.role is not None:
            staff.role = StaffRole(update.role)

        if update.status is not None:
            staff.status = StaffStatus(update.status)

        await self.db.flush()
        return staff

    async def revoke_staff(self, staff_id: UUID) -> "BusinessStaff":
        """Revoke staff membership"""
        staff = await self.get_staff(staff_id)
        if not staff:
            raise NotFoundError("Staff member not found")

        staff.status = "REVOKED"
        await self.db.flush()
        return staff

    async def _get_business(self, business_id: UUID) -> Optional["Business"]:
        from app.db.models.business import Business
        stmt = select(Business).where(Business.id == business_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_branch(self, branch_id: UUID, business_id: UUID) -> Optional["Branch"]:
        from app.db.models.business import Branch
        stmt = select(Branch).where(
            Branch.id == branch_id,
            Branch.business_id == business_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: UUID) -> Optional["User"]:
        from app.db.models.user import User
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()