"""Business API endpoints"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.business_service import BusinessService
from app.services.staff_service import StaffService
from app.schemas.business import (
    BusinessCreate, BusinessUpdate, BusinessResponse, BusinessListResponse,
    BranchCreate, BranchUpdate, BranchResponse, BranchListResponse
)
from app.schemas.staff import (
    BusinessStaffCreate, BusinessStaffUpdate, BusinessStaffResponse, BusinessStaffListResponse
)
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


def get_business_service(db: AsyncSession = Depends(get_db)) -> BusinessService:
    return BusinessService(db)


def get_staff_service(db: AsyncSession = Depends(get_db)) -> StaffService:
    return StaffService(db)


# Business endpoints
@router.post(
    "/businesses",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Businesses"]
)
async def create_business(
    request: Request,
    business_data: BusinessCreate,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Create a new business"""
    # Get current user from auth (would come from auth dependency)
    # For now, use a placeholder - real implementation would get from auth
    owner_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder

    business = await business_service.create_business(owner_id, business_data)
    return business


@router.get("/businesses/me", response_model=BusinessResponse, tags=["Businesses"])
async def get_my_business(
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
):
    """Get current user's business"""
    user_id = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from app.core.security import decode_access_token
        payload = decode_access_token(auth_header.split(" ")[1])
        if payload and "sub" in payload:
            try:
                user_id = UUID(payload["sub"])
            except ValueError:
                pass

    if user_id:
        business = await business_service.get_business_by_owner(user_id)
        if business:
            return business
        # If user has no business yet, create one
        from app.schemas.business import BusinessCreate
        from app.db.models.user import User
        user = await db.get(User, user_id)
        name = user.name if user else "Merchant"
        business = await business_service.create_business(
            user_id,
            BusinessCreate(name=f"{name}'s Store", contact_email=user.email if user else None)
        )
        return business

    owner_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
    business = await business_service.get_business_by_owner(owner_id)
    if not business:
        # Fallback to any existing business in development
        from sqlalchemy import select
        from app.db.models.business import Business
        res = await db.execute(select(Business).limit(1))
        business = res.scalar_one_or_none()
    if not business:
        raise NotFoundError("Business not found")
    return business


@router.get("/businesses/{business_id}", response_model=BusinessResponse, tags=["Businesses"])
async def get_business(
    business_id: UUID,
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Get business by ID"""
    business = await business_service.get_business(business_id)
    if not business:
        raise NotFoundError("Business not found")
    return business


@router.patch("/businesses/{business_id}", response_model=BusinessResponse, tags=["Businesses"])
async def update_business(
    business_id: UUID,
    business_data: BusinessUpdate,
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Update business information"""
    business = await business_service.update_business(business_id, business_data)
    return business


@router.get("/businesses", response_model=BusinessListResponse, tags=["Businesses"])
async def list_businesses(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    verification_status: Optional[str] = None,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """List all businesses (admin)"""
    businesses, total = await business_service.list_businesses(page, page_size, status, verification_status)
    return BusinessListResponse(
        businesses=businesses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post(
    "/businesses/{business_id}/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Branches"]
)
async def create_branch(
    business_id: UUID,
    branch_data: BranchCreate,
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Create a new branch"""
    branch = await business_service.create_branch(business_id, branch_data)
    return branch


@router.get("/businesses/{business_id}/branches", response_model=BranchListResponse, tags=["Branches"])
async def list_branches(
    business_id: UUID,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """List branches for a business"""
    branches, total = await business_service.list_branches(business_id, page, page_size)
    return BranchListResponse(
        branches=branches,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/branches/{branch_id}", response_model=BranchResponse, tags=["Branches"])
async def get_branch(
    branch_id: UUID,
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Get branch by ID"""
    branch = await business_service.get_branch(branch_id)
    if not branch:
        raise NotFoundError("Branch not found")
    return branch


@router.patch("/branches/{branch_id}", response_model=BranchResponse, tags=["Branches"])
async def update_branch(
    branch_id: UUID,
    branch_data: BranchUpdate,
    request: Request,
    business_service: BusinessService = Depends(get_business_service),
    request_id: str = Depends(get_request_id)
):
    """Update branch information"""
    branch = await business_service.update_branch(branch_id, branch_data)
    return branch


# Staff/Cashier endpoints
@router.post(
    "/businesses/{business_id}/staff",
    response_model=BusinessStaffResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Staff"]
)
async def invite_staff(
    business_id: UUID,
    staff_data: BusinessStaffCreate,
    request: Request,
    staff_service: StaffService = Depends(get_staff_service),
    request_id: str = Depends(get_request_id)
):
    """Invite a staff member to the business"""
    invited_by = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
    staff = await staff_service.invite_staff(business_id, staff_data, invited_by)
    return staff


@router.get("/businesses/{business_id}/staff", response_model=BusinessStaffListResponse, tags=["Staff"])
async def list_staff(
    business_id: UUID,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    staff_service: StaffService = Depends(get_staff_service),
    request_id: str = Depends(get_request_id)
):
    """List staff members"""
    staff, total = await staff_service.list_staff(
        business_id, page, page_size,
        branch_id=branch_id, status=status, role=role
    )
    return BusinessStaffListResponse(
        staff=staff,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/staff/{staff_id}", response_model=BusinessStaffResponse, tags=["Staff"])
async def get_staff(
    staff_id: UUID,
    request: Request,
    staff_service: StaffService = Depends(get_staff_service),
    request_id: str = Depends(get_request_id)
):
    """Get staff member by ID"""
    staff = await staff_service.get_staff(staff_id)
    if not staff:
        raise NotFoundError("Staff member not found")
    return staff


@router.patch("/staff/{staff_id}", response_model=BusinessStaffResponse, tags=["Staff"])
async def update_staff(
    staff_id: UUID,
    staff_data: BusinessStaffUpdate,
    request: Request,
    staff_service: StaffService = Depends(get_staff_service),
    request_id: str = Depends(get_request_id)
):
    """Update staff member"""
    staff = await staff_service.update_staff(staff_id, staff_data)
    return staff


@router.post("/staff/{staff_id}/revoke", response_model=BusinessStaffResponse, tags=["Staff"])
async def revoke_staff(
    staff_id: UUID,
    request: Request,
    staff_service: StaffService = Depends(get_staff_service),
    request_id: str = Depends(get_request_id)
):
    """Revoke staff membership"""
    staff = await staff_service.revoke_staff(staff_id)
    return staff