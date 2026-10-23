"""Pytest configuration and fixtures"""
import pytest
import pytest_asyncio
from uuid import uuid4
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import os
import uuid
import tempfile
import shutil

from app.main import create_app
from app.db.database import Base, get_db
from app.db.models.user import User, UserStatus
from app.db.models.wallet import Wallet, WalletStatus
from app.db.models.device import Device, DeviceStatus
from app.core.security import hash_device_key, generate_device_key
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine with unique database file per test"""
    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp(prefix="test_palmpay_")
    test_db_path = os.path.join(temp_dir, "test_palmpay.db")
    
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        # Drop all tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    
    # Clean up the temporary directory after each test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine):
    """Create test database session"""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine):
    """Create test client with overridden database"""
    app = create_app()
    
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(test_db: AsyncSession):
    """Create a test user"""
    user = User(
        name="Test User",
        phone="+1234567890",
        status=UserStatus.ACTIVE
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def test_wallet(test_db: AsyncSession, test_user: User):
    """Create a test wallet"""
    wallet = Wallet(
        user_id=test_user.id,
        balance=Decimal("1000.00"),
        currency="INR",
        status=WalletStatus.ACTIVE
    )
    test_db.add(wallet)
    await test_db.flush()
    return wallet


@pytest_asyncio.fixture(scope="function")
async def test_device(test_db: AsyncSession, test_user: User):
    """Create a test device for the test user"""
    from app.db.models.payment_device import PaymentDevice, DeviceType, PairingStatus, ConnectionStatus
    from app.db.models.business import Business, BusinessStatus
    
    # Create a business owned by the test user
    business = Business(
        name="Test Business",
        owner_id=test_user.id,
        status=BusinessStatus.ACTIVE,
        verification_status="verified"
    )
    test_db.add(business)
    await test_db.flush()
    
    device_key = generate_device_key()
    device = PaymentDevice(
        device_name="Test ESP32",
        device_type=DeviceType.ESP32,
        business_id=business.id,
        device_key_hash=hash_device_key(device_key),
        pairing_status=PairingStatus.PAIRED,
        connection_status=ConnectionStatus.ONLINE
    )
    test_db.add(device)
    await test_db.flush()
    return device, device_key


@pytest.fixture
def mock_image_base64():
    """Generate a mock base64 encoded image"""
    import base64
    import numpy as np
    import cv2

    # Create a simple test image
    img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()