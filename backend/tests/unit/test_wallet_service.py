"""Unit tests for WalletService"""
import pytest
from decimal import Decimal
from app.services.wallet_service import WalletService
from app.schemas.wallets import WalletCreate, WalletTopUpRequest
from app.db.models.wallet import WalletStatus
from app.core.exceptions import NotFoundError, ValidationError, WalletError


@pytest.mark.asyncio
async def test_create_wallet(test_db, test_user):
    """Test creating a wallet"""
    service = WalletService(test_db)
    wallet_data = WalletCreate(user_id=test_user.id, initial_balance=Decimal("100.00"))
    wallet = await service.create_wallet(wallet_data)

    assert wallet.user_id == test_user.id
    assert wallet.balance == Decimal("100.00")
    assert wallet.status == WalletStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_balance(test_db, test_user, test_wallet):
    """Test getting wallet balance"""
    service = WalletService(test_db)
    balance = await service.get_balance(test_user.id)
    assert balance == Decimal("1000.00")


@pytest.mark.asyncio
async def test_check_balance_sufficient(test_db, test_user, test_wallet):
    """Test checking sufficient balance"""
    service = WalletService(test_db)
    has_balance = await service.check_balance(test_user.id, Decimal("500.00"))
    assert has_balance is True


@pytest.mark.asyncio
async def test_check_balance_insufficient(test_db, test_user, test_wallet):
    """Test checking insufficient balance"""
    service = WalletService(test_db)
    has_balance = await service.check_balance(test_user.id, Decimal("2000.00"))
    assert has_balance is False


@pytest.mark.asyncio
async def test_debit_wallet(test_db, test_user, test_wallet):
    """Test debiting wallet"""
    service = WalletService(test_db)
    from uuid import uuid4
    txn_id = uuid4()
    wallet = await service.debit(test_user.id, Decimal("100.00"), txn_id)

    assert wallet.balance == Decimal("900.00")


@pytest.mark.asyncio
async def test_debit_insufficient_fails(test_db, test_user, test_wallet):
    """Test debiting more than balance fails"""
    service = WalletService(test_db)
    from uuid import uuid4
    txn_id = uuid4()

    with pytest.raises(WalletError, match="Insufficient balance"):
        await service.debit(test_user.id, Decimal("2000.00"), txn_id)


@pytest.mark.asyncio
async def test_credit_wallet(test_db, test_user, test_wallet):
    """Test crediting wallet"""
    service = WalletService(test_db)
    from uuid import uuid4
    txn_id = uuid4()
    wallet = await service.credit(test_user.id, Decimal("500.00"), txn_id)

    assert wallet.balance == Decimal("1500.00")


@pytest.mark.asyncio
async def test_freeze_unfreeze_wallet(test_db, test_user, test_wallet):
    """Test freezing and unfreezing wallet"""
    service = WalletService(test_db)

    # Freeze
    wallet = await service.freeze_wallet(test_user.id)
    assert wallet.status == WalletStatus.FROZEN

    # Try to debit frozen wallet
    from uuid import uuid4
    with pytest.raises(WalletError):
        await service.debit(test_user.id, Decimal("100.00"), uuid4())

    # Unfreeze
    wallet = await service.unfreeze_wallet(test_user.id)
    assert wallet.status == WalletStatus.ACTIVE

    # Should work now
    wallet = await service.debit(test_user.id, Decimal("100.00"), uuid4())
    assert wallet.balance == Decimal("900.00")


@pytest.mark.asyncio
async def test_topup_wallet(test_db, test_user, test_wallet):
    """Test admin top-up"""
    service = WalletService(test_db)
    request = WalletTopUpRequest(amount=Decimal("500.00"), description="Test topup")
    wallet = await service.top_up(test_user.id, request)

    assert wallet.balance == Decimal("1500.00")