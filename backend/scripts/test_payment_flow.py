#!/usr/bin/env python
"""Test payment flow"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from uuid import uuid4

sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_db, init_db, close_db
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.payment_service import PaymentService
from app.services.biometric_service import BiometricService
from app.schemas.users import UserCreateInternal
from app.schemas.transactions import PaymentRequest
from app.utils.image import image_processor
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


def create_test_image() -> str:
    """Create a test image"""
    import numpy as np
    import cv2
    import base64

    img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    cv2.circle(img, (112, 112), 80, (100, 50, 30), -1)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode()


async def main():
    """Test complete payment flow"""
    setup_logging()
    await init_db()

    async for db in get_db():
        user_service = UserService(db)
        wallet_service = WalletService(db)
        payment_service = PaymentService(db)
        biometric_service = BiometricService(db)

        # Create user
        user = await user_service.create_user(
            UserCreateInternal(name="Payment Test User", phone="+1999999999")
        )
        print(f"Created user: {user.id}")

        # Create wallet with balance
        wallet = await wallet_service.create_wallet(
            user_id=user.id,
            currency="INR"
        )
        # Add initial balance
        wallet.balance = Decimal("5000.00")
        await db.flush()
        print(f"Created wallet with balance: {wallet.balance}")

        # Enroll biometric
        images = [create_test_image() for _ in range(3)]
        templates, qualities = await biometric_service.enroll_user(user.id, images)
        print(f"Enrolled {len(templates)} biometric templates")
        print(f"Quality scores: {[f'{q:.2f}' for q in qualities]}")

        # Test identification
        matched, user_id, similarity, reason = await biometric_service.identify(images[0])
        print(f"Identification: matched={matched}, user_id={user_id}, similarity={similarity}")

        # Process payment
        payment_request = PaymentRequest(
            user_id=user.id,
            amount=Decimal("100.00"),
            currency="INR",
            description="Test payment"
        )
        idempotency_key = str(uuid4())
        transaction = await payment_service.process_payment(payment_request, idempotency_key)
        print(f"Payment successful: {transaction.transaction_reference}")
        print(f"Amount: {transaction.amount}")
        print(f"Status: {transaction.status}")

        # Check remaining balance
        balance = await wallet_service.get_balance(user.id)
        print(f"Remaining balance: {balance}")

        # Test idempotency
        transaction2 = await payment_service.process_payment(payment_request, idempotency_key)
        print(f"Idempotent request returned same transaction: {transaction.id == transaction2.id}")

        await db.commit()
        break

    await close_db()
    logger.info("Payment flow test complete")


if __name__ == "__main__":
    asyncio.run(main())