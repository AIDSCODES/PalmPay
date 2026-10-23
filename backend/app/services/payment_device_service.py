"""Payment device service"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import secrets
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models.payment_device import PaymentDevice, DeviceType, PairingStatus, ConnectionStatus
from app.db.models.business import Business, Branch
from app.db.models.user import User
from app.schemas.payment_device import PaymentDeviceCreate, PaymentDeviceUpdate, DevicePairRequest
from app.core.security import hash_device_key, verify_device_key, generate_device_key
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, DeviceError

logger = get_logger(__name__)


class PaymentDeviceService:
    """Payment device management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, request: PaymentDeviceCreate) -> tuple["PaymentDevice", str]:
        """Register a new payment device and return device with plaintext key (only time)"""
        device_key = generate_device_key()
        device_key_hash = hash_device_key(device_key)

        # Verify business
        business = await self._get_business(request.business_id)
        if not business:
            raise NotFoundError("Business not found")

        # Verify branch if provided
        if request.branch_id:
            branch = await self._get_branch(request.branch_id, request.business_id)
            if not branch:
                raise NotFoundError("Branch not found")

        device = PaymentDevice(
            device_name=request.device_name,
            device_type=request.device_type,
            firmware_version=request.firmware_version,
            business_id=request.business_id,
            branch_id=request.branch_id,
            device_key_hash=hash_device_key(device_key),
            pairing_status=PairingStatus.UNPAIRED,
            connection_status=ConnectionStatus.OFFLINE
        )
        self.db.add(device)
        await self.db.flush()

        logger.info(f"Device registered: {device.id} ({device.device_name})")
        return device, device_key

    async def get_device(self, device_id: UUID) -> Optional["PaymentDevice"]:
        """Get device by ID"""
        stmt = select(PaymentDevice).where(PaymentDevice.id == device_id).options(
            selectinload(PaymentDevice.branch),
            selectinload(PaymentDevice.business)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def authenticate_device(self, device_id: UUID, device_key: str) -> "PaymentDevice":
        """Authenticate device credentials"""
        stmt = select(PaymentDevice).where(PaymentDevice.id == device_id)
        result = await self.db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            raise DeviceError("Device not found", code="DEVICE_UNAUTHORIZED")

        if not verify_device_key(device_key, device.device_key_hash):
            raise DeviceError("Invalid device key", code="DEVICE_UNAUTHORIZED")

        if device.pairing_status == "REVOKED":
            raise DeviceError("Device has been revoked", code="DEVICE_REVOKED")

        # Update connection status
        device.connection_status = "ONLINE"
        device.last_seen = datetime.utcnow()
        await self.db.flush()

        return device

    async def device_heartbeat(self, device_id: UUID, ip_address: str = None, metadata: str = None) -> "PaymentDevice":
        """Update device heartbeat"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        device.connection_status = "ONLINE"
        device.last_seen = datetime.utcnow()
        if device.connection_status == "OFFLINE":
            device.connection_status = "ONLINE"
        device.ip_address = device.ip_address  # Keep existing or update if needed

        await self.db.flush()
        return device

    async def pair_device(self, device_id: UUID, paired_by: UUID) -> "PaymentDevice":
        """Pair a device with a business"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        if device.pairing_status == "PAIRED":
            raise ValidationError("Device already paired")

        device.pairing_status = "PAIRED"
        device.paired_at = datetime.utcnow()
        device.paired_by = device_id  # This should be the user ID who paired it
        device.connection_status = "ONLINE"
        device.last_seen = datetime.utcnow()
        await self.db.flush()

        return device

    async def unpair_device(self, device_id: UUID) -> "PaymentDevice":
        """Unpair a device"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        if device.pairing_status != "PAIRED":
            raise ValidationError("Device is not paired")

        device.pairing_status = "UNPAIRED"
        device.paired_at = None
        device.paired_by = None
        device.connection_status = "OFFLINE"
        await self.db.flush()

        return device

    async def revoke_device(self, device_id: UUID) -> "PaymentDevice":
        """Revoke a device"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        device.pairing_status = "REVOKED"
        device.connection_status = "OFFLINE"
        await self.db.flush()
        return device

    async def activate_device(self, device_id: UUID) -> "PaymentDevice":
        """Activate a pending device"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        device.pairing_status = "PAIRED"
        device.connection_status = "ONLINE"
        device.last_seen = datetime.utcnow()
        await self.db.flush()
        return device

    async def list_devices(
        self,
        business_id: UUID,
        page: int = 1,
        page_size: int = 20,
        branch_id: Optional[str] = None,
        pairing_status: Optional[str] = None,
        connection_status: Optional[str] = None
    ) -> tuple[List["PaymentDevice"], int]:
        """List devices with pagination"""
        from app.db.models.payment_device import PairingStatus, ConnectionStatus

        stmt = select(PaymentDevice).where(PaymentDevice.business_id == business_id)

        if branch_id:
            stmt = stmt.where(PaymentDevice.branch_id == UUID(branch_id))
        if pairing_status:
            stmt = stmt.where(PaymentDevice.pairing_status == PairingStatus(pairing_status))
        if connection_status:
            stmt = stmt.where(PaymentDevice.connection_status == ConnectionStatus(connection_status))

        # Count total
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(PaymentDevice.created_at.desc())

        result = await self.db.execute(stmt)
        devices = list(result.scalars().all())

        return devices, total

    async def update_device(self, device_id: UUID, update: "PaymentDeviceUpdate") -> "PaymentDevice":
        """Update device information"""
        device = await self.get_device(device_id)
        if not device:
            raise NotFoundError("Device not found")

        if update.device_name is not None:
            device.device_name = update.device_name
        if update.firmware_version is not None:
            device.firmware_version = update.firmware_version
        if update.branch_id is not None:
            branch = await self._get_branch(update.branch_id, None)
            if not branch:
                raise NotFoundError("Branch not found")
            device.branch_id = update.branch_id
        if update.pairing_status is not None:
            device.pairing_status = update.pairing_status
        if update.connection_status is not None:
            device.connection_status = update.connection_status

        await self.db.flush()
        return device

    async def _get_business(self, business_id: str):
        from app.db.models.business import Business
        stmt = select(Business).where(Business.id == business_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_branch(self, branch_id: str, business_id: str = None):
        from app.db.models.business import Branch
        stmt = select(Branch).where(Branch.id == UUID(branch_id))
        if business_id:
            stmt = stmt.where(Branch.business_id == UUID(business_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()