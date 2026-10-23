#!/usr/bin/env python
"""Create admin user and device script"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_db, init_db, close_db
from app.services.user_service import UserService
from app.services.device_service import DeviceService
from app.services.wallet_service import WalletService
from app.schemas.users import UserCreateInternal
from app.schemas.devices import DeviceRegisterRequest
from app.db.models.user import UserStatus
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def main():
    """Create admin user and device"""
    setup_logging()
    await init_db()

    async for db in get_db():
        user_service = UserService(db)
        device_service = DeviceService(db)
        wallet_service = WalletService(db)

        # Create admin user
        admin_user = await user_service.create_user(
            UserCreateInternal(name="Admin User", phone="+1000000000")
        )
        logger.info(f"Created admin user: {admin_user.id}")

        # Create wallet for admin
        await wallet_service.create_wallet(admin_user.id, currency="INR")
        logger.info(f"Created wallet for admin")

        # Create test device
        device, device_key = await device_service.register_device(
            DeviceRegisterRequest(device_name="Admin ESP32")
        )
        await device_service.activate_device(device.id)
        logger.info(f"Created device: {device.id}")
        logger.info(f"Device key: {device_key}")

        await db.commit()
        break

    await close_db()
    logger.info("Setup complete")


if __name__ == "__main__":
    asyncio.run(main())