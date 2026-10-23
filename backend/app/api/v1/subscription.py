"""Subscription API endpoints"""
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import (
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse, SubscriptionListResponse
)
from app.core.security import generate_request_id
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_subscription_service(db: AsyncSession = Depends(get_db)) -> "SubscriptionService":
    from app.services.subscription_service import SubscriptionService
    return SubscriptionService(db)


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Subscriptions"]
)
async def create_subscription(
    request: Request,
    subscription_data: SubscriptionCreate,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Create a new subscription for a business"""
    # Get business from current user (placeholder)
    business_id = UUID("00000000-0000-0000-0000-000000000001")

    subscription = await subscription_service.create_subscription(subscription_data)
    return SubscriptionResponse.model_validate(subscription)


@router.get("/subscriptions/me", response_model=SubscriptionResponse, tags=["Subscriptions"])
async def get_my_subscription(
    request: Request,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Get current business's subscription"""
    business_id = UUID("00000000-0000-0000-0000-000000000001")

    subscription = await subscription_service.get_active_subscription(business_id)
    if not subscription:
        raise NotFoundError("No active subscription found")
    return SubscriptionResponse.model_validate(subscription)


@router.get("/subscriptions/me/plan", tags=["Subscriptions"])
async def get_plan_details(
    request: Request,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Get available plan details"""
    from app.services.subscription_service import SubscriptionService
    return SubscriptionService.PLAN_DETAILS


@router.patch("/subscriptions/me", response_model=SubscriptionResponse, tags=["Subscriptions"])
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    request: Request,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Update subscription (change plan, billing interval, etc.)"""
    business_id = UUID("00000000-0000-0000-0000-000000000001")
    subscription = await subscription_service.get_active_subscription(business_id)
    if not subscription:
        raise NotFoundError("No active subscription found")

    subscription = await subscription_service.update_subscription(subscription.id, subscription_data)
    return SubscriptionResponse.model_validate(subscription)


@router.post("/subscriptions/me/cancel", tags=["Subscriptions"])
async def cancel_subscription(
    request: Request,
    immediate: bool = False,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Cancel subscription"""
    business_id = UUID("00000000-0000-0000-0000-000000000001")
    subscription = await subscription_service.get_active_subscription(business_id)
    if not subscription:
        raise NotFoundError("No active subscription found")

    subscription = await subscription_service.cancel_subscription(subscription.id, immediate)
    return {"message": "Subscription cancelled", "subscription": SubscriptionResponse.model_validate(subscription)}


@router.get("/subscriptions", response_model=SubscriptionListResponse, tags=["Subscriptions", "Admin"])
async def list_subscriptions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    plan: Optional[str] = None,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """List all subscriptions (admin)"""
    subscriptions, total = await subscription_service.list_subscriptions(page, page_size, status, plan)
    return SubscriptionListResponse(
        subscriptions=subscriptions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse, tags=["Subscriptions", "Admin"])
async def get_subscription(
    subscription_id: UUID,
    request: Request,
    subscription_service: "SubscriptionService" = Depends(get_subscription_service),
    request_id: str = Depends(get_request_id)
):
    """Get subscription by ID"""
    subscription = await subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise NotFoundError("Subscription not found")
    return SubscriptionResponse.model_validate(subscription)