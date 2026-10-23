"""Device service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import secrets
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.device import Device, DeviceStatus
from app.core.security import hash_device_key, verify_device_key, generate_device_key
from app.schemas.devices import DeviceRegisterRequest
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, DeviceError

logger = get_logger(__name__)


class DeviceService:
    """Device management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, request: DeviceRegisterRequest) -> tuple[Device, str]:
        """Register a new device and return device with plaintext key (only time)"""
        device_key = generate_device_key()
        device_key_hash = hash_device_key(device_key)

        device = Device(
            device_name=request.device_name,
            device_key_hash=device_key_hash,
            status=DeviceStatus.PENDING
        )
        self.db.add(device)
        await self.db.flush()

        logger.info(f"Device registered: {device.id} ({device.device_name})")
        return device, device_key

    async def authenticate_device(self, device_id: UUID, device_key: str) -> Device:
        """Authenticate device credentials"""
        stmt = select(Device).where(Device.id == device_id)
        result = await self.db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            raise DeviceError("Device not found", code="DEVICE_UNAUTHORIZED")

        if not verify_device_key(device_key, device.device_key_hash):
            raise DeviceError("Invalid device key", code="DEVICE_UNAUTHORIZED")

        if device.status == DeviceStatus.REVOKED:
            raise DeviceError("Device has been revoked", code="DEVICE_REVOKED")

        if device.status == DeviceStatus.PENDING:
            device.status = DeviceStatus.ACTIVE

        device.last_seen = datetime.utcnow()
        await self.db.flush()

        return device

    async def get_device(self, device_id: UUID) -> Optional[Device]:
        """Get device by ID"""
        stmt = select(Device).where(Device.id == device_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_device(self, device_id: UUID) -> Device:
        """Revoke a device"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        device.status = DeviceStatus.REVOKED
        await self.db.flush()
        return device

    async def activate_device(self, device_id: UUID) -> Device:
        """Activate a pending device"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        device.status = DeviceStatus.ACTIVE
        await self.db.flush()
        return device

    async def list_devices(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DeviceStatus] = None
    ) -> tuple[List[Device], int]:
        """List devices with pagination"""
        stmt = select(Device)

        if status:
            stmt = stmt.where(Device.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Device.created_at.desc())

        result = await self.db.execute(stmt)
        devices = list(result.scalars().all())

        return devices, total