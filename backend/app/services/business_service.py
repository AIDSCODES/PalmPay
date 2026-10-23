"""Business service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.business import Business, BusinessStatus, Branch, BranchStatus
from app.db.models.user import User
from app.schemas.business import BusinessCreate, BusinessUpdate, BranchCreate, BranchUpdate
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, ValidationError

logger = get_logger(__name__)


class BusinessService:
    """Business management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Business methods
    async def create_business(self, owner_id: UUID, request: BusinessCreate) -> "Business":
        """Create a new business"""
        owner = await self.db.get(User, owner_id)
        if not owner:
            raise NotFoundError("Owner not found")

        business = Business(
            name=request.name,
            legal_name=request.legal_name,
            business_type=request.business_type,
            description=request.description,
            owner_id=owner_id,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            address=request.address,
            gst_number=request.gst_number,
            status=BusinessStatus.PENDING
        )
        self.db.add(business)
        await self.db.flush()

        # Add owner as business staff
        from app.db.models.staff import BusinessStaff, StaffRole, StaffStatus
        staff = BusinessStaff(
            business_id=business.id,
            user_id=owner_id,
            role="OWNER",
            status="ACTIVE",
            invited_by=owner_id,
            joined_at=datetime.utcnow()
        )
        self.db.add(staff)
        await self.db.flush()

        return business

    async def get_business(self, business_id: UUID) -> Optional["Business"]:
        stmt = select(Business).where(Business.id == business_id).options(
            selectinload(Business.branches),
            selectinload(Business.staff)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_business_by_owner(self, owner_id: UUID) -> Optional["Business"]:
        stmt = select(Business).where(Business.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_business(self, business_id: UUID, update: BusinessUpdate) -> "Business":
        business = await self.get_business(business_id)
        if not business:
            raise NotFoundError("Business not found")

        if update.name is not None:
            business.name = update.name
        if update.legal_name is not None:
            business.legal_name = update.legal_name
        if update.business_type is not None:
            business.business_type = update.business_type
        if update.description is not None:
            business.description = update.description
        if update.contact_email is not None:
            business.contact_email = update.contact_email
        if update.contact_phone is not None:
            business.contact_phone = update.contact_phone
        if update.address is not None:
            business.address = update.address
        if update.gst_number is not None:
            business.gst_number = update.gst_number
        if update.status is not None:
            business.status = BusinessStatus(update.status)

        await self.db.flush()
        return business

    async def verify_business(self, business_id: UUID, status: str) -> "Business":
        """Verify or reject a business (admin)"""
        business = await self.get_business(business_id)
        if not business:
            raise NotFoundError("Business not found")

        if status == "verified":
            business.verification_status = "verified"
            business.status = BusinessStatus.ACTIVE
        elif status == "rejected":
            business.verification_status = "rejected"
            business.status = BusinessStatus.REJECTED

        await self.db.flush()
        return business

    async def list_businesses(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        verification_status: Optional[str] = None
    ) -> tuple[List["Business"], int]:
        stmt = select(Business)

        if status:
            stmt = stmt.where(Business.status == BusinessStatus(status))
        if verification_status:
            stmt = stmt.where(Business.verification_status == verification_status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Business.created_at.desc())

        result = await self.db.execute(stmt)
        businesses = list(result.scalars().all())

        return businesses, total

    # Branch methods
    async def create_branch(self, business_id: UUID, request: BranchCreate) -> "Branch":
        business = await self.get_business(business_id)
        if not business:
            raise NotFoundError("Business not found")

        branch = Branch(
            business_id=business_id,
            name=request.name,
            address=request.address,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
            phone=request.phone,
            email=request.email,
            status=BranchStatus.ACTIVE
        )
        self.db.add(branch)
        await self.db.flush()
        return branch

    async def get_branch(self, branch_id: UUID) -> Optional["Branch"]:
        stmt = select(Branch).where(Branch.id == branch_id).options(
            selectinload(Branch.devices),
            selectinload(Branch.staff)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_branch(self, branch_id: UUID, update: BranchUpdate) -> "Branch":
        branch = await self.get_branch(branch_id)
        if not branch:
            raise NotFoundError("Branch not found")

        if update.name is not None:
            branch.name = update.name
        if update.address is not None:
            branch.address = update.address
        if update.city is not None:
            branch.city = update.city
        if update.state is not None:
            branch.state = update.state
        if update.pincode is not None:
            branch.pincode = update.pincode
        if update.phone is not None:
            branch.phone = update.phone
        if update.email is not None:
            branch.email = update.email
        if update.status is not None:
            branch.status = BranchStatus(update.status)

        await self.db.flush()
        return branch

    async def list_branches(
        self,
        business_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> tuple[List["Branch"], int]:
        from app.db.models.business import BranchStatus
        stmt = select(Branch).where(Branch.business_id == business_id)

        if status:
            stmt = stmt.where(Branch.status == BranchStatus(status))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Branch.created_at.desc())

        result = await self.db.execute(stmt)
        branches = list(result.scalars().all())

        return branches, total