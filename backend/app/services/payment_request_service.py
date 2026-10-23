"""Payment request service with state machine"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.payment_request import PaymentRequest, PaymentRequestStatus
from app.db.models.business import Business, Branch
from app.db.models.payment_device import PaymentDevice, PairingStatus, ConnectionStatus
from app.db.models.user import User
from app.db.models.transaction import Transaction, TransactionType, TransactionStatus
from app.schemas.payment_request import PaymentRequestCreate, PaymentRequestUpdate, VALID_STATUS_TRANSITIONS
from app.services.payment_service import PaymentService
from app.services.biometric_service import BiometricService
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, PaymentError

logger = get_logger(__name__)


class PaymentRequestService:
    """Payment request service with state machine"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_service = PaymentService(db)
        self.biometric_service = BiometricService(db)

    def _generate_request_reference(self) -> str:
        import uuid
        return f"PR-{uuid.uuid4().hex[:12].upper()}"

    async def create_payment_request(
        self,
        request: PaymentRequestCreate,
        created_by: UUID
    ) -> "PaymentRequest":
        """Create a new payment request"""
        # Verify business
        business = await self._get_business(request.business_id)
        if not business:
            raise NotFoundError("Business not found")

        # Verify branch if provided
        if request.branch_id:
            branch = await self._get_branch(request.branch_id, request.business_id)
            if not branch:
                raise NotFoundError("Branch not found")

        # Verify device if provided
        device = None
        if request.device_id:
            device = await self._get_device(request.device_id)
            if not device:
                raise NotFoundError("Device not found")
            if device.pairing_status != "PAIRED":
                raise ValidationError("Device is not paired")
            if device.connection_status != "ONLINE":
                raise ValidationError("Device is offline")

        # Verify creator has permission
        await self._verify_business_permission(request.business_id, created_by)

        # Validate amount
        if request.amount <= 0:
            raise ValidationError("Amount must be positive")

        # Check idempotency
        if request.idempotency_key:
            existing = await self.get_by_idempotency_key(request.idempotency_key)
            if existing:
                raise ConflictError("Idempotency key already used", code="IDEMPOTENCY_CONFLICT")

        # Set expiry (default 10 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        payment_request = PaymentRequest(
            request_reference=self._generate_request_reference(),
            business_id=request.business_id,
            branch_id=request.branch_id,
            device_id=request.device_id,
            created_by=created_by,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            idempotency_key=request.idempotency_key,
            expires_at=expires_at,
            status=PaymentRequestStatus.CREATED
        )

        self.db.add(payment_request)
        await self.db.flush()

        # If device specified, send to device
        if device:
            await self.send_to_device(payment_request.id)

        return payment_request

    async def get_payment_request(self, request_id: UUID) -> Optional["PaymentRequest"]:
        stmt = select(PaymentRequest).where(PaymentRequest.id == request_id).options(
            selectinload(PaymentRequest.branch),
            selectinload(PaymentRequest.device),
            selectinload(PaymentRequest.creator),
            selectinload(PaymentRequest.transaction)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional["PaymentRequest"]:
        stmt = select(PaymentRequest).where(PaymentRequest.idempotency_key == idempotency_key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def send_to_device(self, request_id: UUID) -> "PaymentRequest":
        """Send payment request to device via WebSocket/polling"""
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        if payment_request.status != PaymentRequestStatus.CREATED:
            raise ValidationError("Can only send CREATED requests to device")

        if not payment_request.device_id:
            raise ValidationError("No device assigned to this payment request")

        device = await self._get_device(payment_request.device_id)
        if not device:
            raise NotFoundError("Device not found")

        if device.pairing_status != "PAIRED":
            raise ValidationError("Device is not paired")

        if device.connection_status != "ONLINE":
            raise ValidationError("Device is offline")

        # Update state
        payment_request.status = PaymentRequestStatus.SENT_TO_DEVICE
        payment_request.sent_to_device_at = datetime.utcnow()
        await self.db.flush()

        # In real implementation, send via WebSocket
        # For now, we just update the state
        logger.info(f"Payment request {payment_request.request_reference} sent to device {payment_request.device_id}")

        return payment_request

    async def device_acknowledge(self, request_id: UUID, device_id: UUID) -> "PaymentRequest":
        """Device acknowledges receipt of payment request"""
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        if payment_request.device_id != device_id:
            raise ValidationError("Device not assigned to this request")

        if payment_request.status != PaymentRequestStatus.SENT_TO_DEVICE:
            raise ValidationError("Request not in SENT_TO_DEVICE state")

        payment_request.status = PaymentRequestStatus.AWAITING_CUSTOMER
        payment_request.device_acknowledged_at = datetime.utcnow()
        await self.db.flush()

        return payment_request

    async def customer_identified(
        self,
        request_id: UUID,
        customer_user_id: UUID,
        biometric_verified: bool = True
    ) -> "PaymentRequest":
        """Mark customer as identified and start processing"""
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        if payment_request.status != PaymentRequestStatus.AWAITING_CUSTOMER:
            raise ValidationError("Request not awaiting customer")

        if not biometric_verified:
            raise ValidationError("Biometric verification failed")

        payment_request.status = PaymentRequestStatus.PROCESSING
        payment_request.customer_identified_at = datetime.utcnow()
        payment_request.customer_user_id = customer_user_id
        payment_request.processing_started_at = datetime.utcnow()
        await self.db.flush()

        # Process payment
        await self._process_payment(payment_request.id)

        return payment_request

    async def _process_payment(self, request_id: UUID) -> "PaymentRequest":
        """Process the payment using the payment service"""
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        if payment_request.status != PaymentRequestStatus.PROCESSING:
            raise ValidationError("Request not in PROCESSING state")

        if not payment_request.customer_user_id:
            raise ValidationError("No customer identified")

        try:
            # Create payment request for payment service
            from app.schemas.transactions import PaymentRequest as PaymentSchemaRequest
            payment_data = PaymentSchemaRequest(
                user_id=payment_request.customer_user_id,
                amount=payment_request.amount,
                currency=payment_request.currency,
                merchant_id=payment_request.business.owner_id if payment_request.business else None,
                description=payment_request.description
            )

            # Process payment
            transaction = await self.payment_service.process_payment(payment_data)

            # Update payment request
            payment_request.status = PaymentRequestStatus.SUCCEEDED
            payment_request.transaction_id = transaction.id
            payment_request.processing_completed_at = datetime.utcnow()
            await self.db.flush()

            return payment_request

        except Exception as e:
            payment_request.status = PaymentRequestStatus.FAILED
            payment_request.failure_reason = str(e)
            payment_request.processing_completed_at = datetime.utcnow()
            await self.db.flush()
            raise PaymentError(f"Payment processing failed: {e}")

    async def cancel_payment_request(self, request_id: UUID, cancelled_by: UUID) -> "PaymentRequest":
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        # Verify permission
        await self._verify_business_permission(payment_request.business_id, cancelled_by)

        if not payment_request.can_transition_to(PaymentRequestStatus.CANCELLED):
            raise ValidationError(f"Cannot cancel from {payment_request.status} state")

        payment_request.status = PaymentRequestStatus.CANCELLED
        await self.db.flush()

        return payment_request

    async def expire_payment_request(self, request_id: UUID) -> "PaymentRequest":
        """Mark expired payment request"""
        payment_request = await self.get_payment_request(request_id)
        if not payment_request:
            raise NotFoundError("Payment request not found")

        if payment_request.status not in [PaymentRequestStatus.CREATED, PaymentRequestStatus.SENT_TO_DEVICE, PaymentRequestStatus.AWAITING_CUSTOMER]:
            return payment_request

        payment_request.status = PaymentRequestStatus.EXPIRED
        await self.db.flush()
        return payment_request

    async def list_payment_requests(
        self,
        business_id: UUID,
        page: int = 1,
        page_size: int = 20,
        branch_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List["PaymentRequest"], int]:
        from app.db.models.payment_request import PaymentRequestStatus

        stmt = select(PaymentRequest).where(PaymentRequest.business_id == business_id).options(
            selectinload(PaymentRequest.branch),
            selectinload(PaymentRequest.device)
        )

        if branch_id:
            stmt = stmt.where(PaymentRequest.branch_id == branch_id)
        if status:
            stmt = stmt.where(PaymentRequest.status == PaymentRequestStatus(status))

        if start_date:
            stmt = stmt.where(PaymentRequest.created_at >= start_date)
        if end_date:
            stmt = stmt.where(PaymentRequest.created_at <= end_date)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(PaymentRequest.created_at.desc())

        result = await self.db.execute(stmt)
        requests = list(result.scalars().all())

        return requests, total

    async def _get_business(self, business_id: UUID):
        stmt = select(Business).where(Business.id == business_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_branch(self, branch_id: UUID, business_id: UUID):
        from app.db.models.business import Branch
        stmt = select(Branch).where(Branch.id == branch_id, Branch.business_id == business_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_device(self, device_id: UUID):
        from app.db.models.payment_device import PaymentDevice
        stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _verify_business_permission(self, business_id: UUID, user_id: UUID):
        """Verify user has permission to access business"""
        from app.db.models.business import Business
        from app.db.models.staff import BusinessStaff, StaffRole

        # Check if owner
        business = await self._get_business(business_id)
        if business.owner_id == user_id:
            return True

        # Check if staff member
        stmt = select(BusinessStaff).where(
            BusinessStaff.business_id == business_id,
            BusinessStaff.user_id == UUID(user_id) if isinstance(user_id, str) else user_id,
            BusinessStaff.status == "ACTIVE"
        )
        result = await self.db.execute(stmt)
        staff = result.scalar_one_or_none()

        if not staff:
            raise ValidationError("No permission for this business")

        return True