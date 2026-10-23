"""Unit tests for PaymentService"""
import pytest
from uuid import uuid4
from decimal import Decimal
from app.services.payment_service import PaymentService
from app.schemas.transactions import PaymentRequest
from app.db.models.user import UserStatus
from app.core.exceptions import NotFoundError, ValidationError, WalletError, IdempotencyError


@pytest.mark.asyncio
async def test_process_payment_success(test_db, test_user, test_wallet):
    """Test successful payment"""
    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=test_user.id,
        amount=Decimal("100.00"),
        currency="INR"
    )

    transaction = await service.process_payment(request)

    assert transaction.status.value == "SUCCESS"
    assert transaction.amount == Decimal("100.00")
    assert transaction.transaction_type.value == "PAYMENT"


@pytest.mark.asyncio
async def test_process_payment_insufficient_balance(test_db, test_user, test_wallet):
    """Test payment with insufficient balance"""
    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=test_user.id,
        amount=Decimal("2000.00"),
        currency="INR"
    )

    with pytest.raises(WalletError, match="Insufficient balance"):
        await service.process_payment(request)


@pytest.mark.asyncio
async def test_process_payment_user_not_found(test_db, test_wallet):
    """Test payment for non-existent user"""
    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=uuid4(),
        amount=Decimal("100.00"),
        currency="INR"
    )

    with pytest.raises(NotFoundError, match="User not found"):
        await service.process_payment(request)


@pytest.mark.asyncio
async def test_process_payment_suspended_user(test_db, test_user, test_wallet):
    """Test payment for suspended user"""
    from app.services.user_service import UserService
    user_service = UserService(test_db)
    await user_service.suspend_user(test_user.id)

    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=test_user.id,
        amount=Decimal("100.00"),
        currency="INR"
    )

    with pytest.raises(ValidationError, match="User account is SUSPENDED"):
        await service.process_payment(request)


@pytest.mark.asyncio
async def test_process_payment_idempotency(test_db, test_user, test_wallet):
    """Test idempotent payment processing"""
    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=test_user.id,
        amount=Decimal("100.00"),
        currency="INR"
    )
    idempotency_key = "123e4567-e89b-12d3-a456-426614174000"

    # First request
    txn1 = await service.process_payment(request, idempotency_key)

    # Second request with same key
    txn2 = await service.process_payment(request, idempotency_key)

    # Should return same transaction
    assert txn1.id == txn2.id
    assert txn1.transaction_reference == txn2.transaction_reference


@pytest.mark.asyncio
async def test_process_payment_negative_amount(test_db, test_user, test_wallet):
    """Test payment with negative amount fails"""
    service = PaymentService(test_db)
    request = PaymentRequest(
        user_id=test_user.id,
        amount=Decimal("-100.00"),
        currency="INR"
    )

    with pytest.raises(ValidationError):
        await service.process_payment(request)