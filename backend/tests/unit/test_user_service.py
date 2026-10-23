"""Unit tests for UserService"""
import pytest
from uuid import uuid4
from decimal import Decimal
from app.services.user_service import UserService
from app.schemas.users import UserCreateInternal, UserUpdate
from app.db.models.user import UserStatus
from app.core.exceptions import NotFoundError, ConflictError, ValidationError


@pytest.mark.asyncio
async def test_create_user(test_db):
    """Test creating a new user"""
    service = UserService(test_db)
    user_data = UserCreateInternal(name="John Doe", phone="+1234567890")
    user = await service.create_user(user_data)

    assert user.name == "John Doe"
    assert user.phone == "+1234567890"
    assert user.status == UserStatus.ACTIVE
    assert user.id is not None


@pytest.mark.asyncio
async def test_create_user_duplicate_phone(test_db):
    """Test creating user with duplicate phone fails"""
    service = UserService(test_db)
    user_data = UserCreateInternal(name="John Doe", phone="+1234567890")
    await service.create_user(user_data)

    # Try to create another user with same phone
    user_data2 = UserCreateInternal(name="Jane Doe", phone="+1234567890")
    with pytest.raises(ConflictError):
        await service.create_user(user_data2)


@pytest.mark.asyncio
async def test_get_user(test_db, test_user):
    """Test getting user by ID"""
    service = UserService(test_db)
    user = await service.get_user(test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.name == test_user.name


@pytest.mark.asyncio
async def test_get_nonexistent_user(test_db):
    """Test getting non-existent user returns None"""
    service = UserService(test_db)
    user = await service.get_user(uuid4())
    assert user is None


@pytest.mark.asyncio
async def test_update_user(test_db, test_user):
    """Test updating user"""
    service = UserService(test_db)
    update_data = UserUpdate(name="Updated Name")
    updated = await service.update_user(test_user.id, update_data)

    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_suspend_user(test_db, test_user):
    """Test suspending user"""
    service = UserService(test_db)
    suspended = await service.suspend_user(test_user.id)

    assert suspended.status == UserStatus.SUSPENDED


@pytest.mark.asyncio
async def test_reactivate_user(test_db, test_user):
    """Test reactivating suspended user"""
    service = UserService(test_db)
    await service.suspend_user(test_user.id)
    reactivated = await service.reactivate_user(test_user.id)

    assert reactivated.status == UserStatus.ACTIVE


@pytest.mark.asyncio
async def test_deactivate_user(test_db, test_user):
    """Test deactivating user"""
    service = UserService(test_db)
    deactivated = await service.deactivate_user(test_user.id)

    assert deactivated.status == UserStatus.DELETED


@pytest.mark.asyncio
async def test_cannot_reactivate_deleted_user(test_db, test_user):
    """Test that deleted users cannot be reactivated"""
    service = UserService(test_db)
    await service.deactivate_user(test_user.id)

    with pytest.raises(ValidationError):
        await service.reactivate_user(test_user.id)