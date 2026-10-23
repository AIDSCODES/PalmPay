"""Subscription service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, BillingInterval
from app.db.models.business import Business
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError

logger = get_logger(__name__)


class SubscriptionService:
    """Subscription management service"""

    PLAN_DETAILS = {
        SubscriptionPlan.FREE: {
            "amount": Decimal("0.00"),
            "features": ["Basic transactions", "Up to 5 devices", "Standard support"]
        },
        SubscriptionPlan.BASIC: {
            "amount": Decimal("999.00"),
            "billing_interval_monthly": True,
            "features": ["Unlimited transactions", "Up to 20 devices", "Priority support", "Analytics dashboard"]
        },
        SubscriptionPlan.PROFESSIONAL: {
            "amount": Decimal("2999.00"),
            "billing_interval_monthly": True,
            "features": ["Unlimited transactions", "Unlimited devices", "Priority support", "Advanced analytics", "Multi-branch support", "API access"]
        },
        SubscriptionPlan.ENTERPRISE: {
            "amount": Decimal("9999.00"),
            "billing_interval_monthly": True,
            "features": ["Everything in Professional", "Custom integrations", "Dedicated support", "SLA guarantee", "Custom contracts"]
        }
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, request: "SubscriptionCreate") -> "Subscription":
        """Create a new subscription"""
        business = await self._get_business(request.business_id)
        if not business:
            raise NotFoundError("Business not found")

        # Check existing active subscription
        existing = await self.get_active_subscription(request.business_id)
        if existing:
            raise ConflictError("Business already has an active subscription")

        plan_details = self.PLAN_DETAILS.get(request.plan, {})
        amount = request.amount or plan_details.get("amount", Decimal("0.00"))

        # Calculate trial period
        trial_days = request.trial_days or 0
        trial_started_at = datetime.utcnow() if trial_days > 0 else None
        trial_ends_at = datetime.utcnow() + timedelta(days=trial_days) if trial_days > 0 else None

        subscription = Subscription(
            business_id=request.business_id,
            plan=request.plan,
            billing_interval=request.billing_interval,
            amount=amount,
            currency=request.currency,
            status=SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE,
            trial_started_at=trial_started_at,
            trial_ends_at=trial_ends_at,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30) if request.billing_interval == "MONTHLY" else datetime.utcnow() + timedelta(days=365)
        )

        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def get_subscription(self, subscription_id: UUID) -> Optional["Subscription"]:
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subscription_by_business(self, business_id: UUID) -> Optional["Subscription"]:
        stmt = select(Subscription).where(
            Subscription.business_id == request.business_id if isinstance(request, str) else UUID(business_id),
            Subscription.status.in_(["ACTIVE", "TRIALING", "PAST_DUE"])
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_subscription(self, business_id: UUID) -> Optional["Subscription"]:
        stmt = select(Subscription).where(
            Subscription.business_id == UUID(business_id) if isinstance(business_id, str) else business_id,
            Subscription.status.in_(["ACTIVE", "TRIALING", "PAST_DUE"])
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_subscription(self, subscription_id: UUID, update: "SubscriptionUpdate") -> "Subscription":
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            raise NotFoundError("Subscription not found")

        if update.plan is not None:
            subscription.plan = update.plan
            plan_details = self.PLAN_DETAILS.get(update.plan, {})
            if update.amount is None:
                subscription.amount = plan_details.get("amount", subscription.amount)

        if update.billing_interval is not None:
            subscription.billing_interval = update.billing_interval

        if update.amount is not None:
            subscription.amount = update.amount

        if update.currency is not None:
            subscription.currency = update.currency

        if update.cancel_at_period_end is not None:
            subscription.cancel_at_period_end = update.cancel_at_period_end

        await self.db.flush()
        return subscription

    async def cancel_subscription(self, subscription_id: UUID, immediate: bool = False) -> "Subscription":
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            raise NotFoundError("Subscription not found")

        if immediate:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
        else:
            subscription.cancel_at_period_end = True

        await self.db.flush()
        return subscription

    async def renew_subscription(self, subscription_id: UUID) -> "Subscription":
        """Renew subscription for next billing period"""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            raise NotFoundError("Subscription not found")

        if subscription.billing_interval == "MONTHLY":
            days = 30
        else:
            days = 365

        subscription.current_period_start = subscription.current_period_end or datetime.utcnow()
        subscription.current_period_end = (subscription.current_period_end or datetime.utcnow()) + timedelta(days=days)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False

        await self.db.flush()
        return subscription

    async def list_subscriptions(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        plan: Optional[str] = None
    ) -> tuple[List["Subscription"], int]:
        from app.db.models.subscription import SubscriptionStatus, SubscriptionPlan

        stmt = select(Subscription)

        if status:
            stmt = stmt.where(Subscription.status == SubscriptionStatus(status))
        if plan:
            stmt = stmt.where(Subscription.plan == SubscriptionPlan(plan))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Subscription.created_at.desc())

        result = await self.db.execute(stmt)
        subscriptions = list(result.scalars().all())

        return subscriptions, total

    async def check_expired_trials(self) -> List["Subscription"]:
        """Check and update expired trials"""
        stmt = select(Subscription).where(
            Subscription.status == "TRIALING",
            Subscription.trial_ends_at < datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        trials = list(result.scalars().all())

        for trial in trials:
            trial.status = SubscriptionStatus.CANCELLED

        if trials:
            await self.db.commit()

        return trials

    async def check_expiring_subscriptions(self, days_ahead: int = 7) -> List["Subscription"]:
        """Find subscriptions expiring soon"""
        future_date = datetime.utcnow() + timedelta(days=days_ahead)
        stmt = select(Subscription).where(
            Subscription.status == "ACTIVE",
            Subscription.current_period_end <= future_date,
            Subscription.cancel_at_period_end == False
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def get_plan_details(self, plan: "SubscriptionPlan") -> dict:
        return self.PLAN_DETAILS.get(plan, {})