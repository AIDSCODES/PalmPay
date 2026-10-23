"""Input validators"""
import base64
import re
from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, validator
from app.core.exceptions import ValidationError


def validate_base64_image(base64_str: str) -> bool:
    """Validate base64 encoded image"""
    try:
        # Remove data URL prefix
        if base64_str.startswith("data:image"):
            base64_str = base64_str.split(",")[1]

        # Decode to check validity
        base64.b64decode(base64_str, validate=True)
        return True
    except Exception:
        return False


def validate_uuid(uuid_str: str) -> UUID:
    """Validate and parse UUID string"""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise ValidationError(f"Invalid UUID format: {uuid_str}")


def validate_amount(amount: Decimal, min_amount: Decimal = Decimal("0.01")) -> Decimal:
    """Validate payment amount"""
    if amount < min_amount:
        raise ValidationError(f"Amount must be at least {min_amount}")
    if amount > Decimal("1000000"):
        raise ValidationError("Amount exceeds maximum limit")
    return amount


def validate_currency(currency: str) -> str:
    """Validate currency code"""
    if not re.match(r"^[A-Z]{3}$", currency):
        raise ValidationError("Currency must be 3-letter ISO code")
    return currency


def validate_phone(phone: Optional[str]) -> Optional[str]:
    """Validate phone number"""
    if phone is None:
        return None
    if not re.match(r"^\+?[1-9]\d{1,14}$", phone):
        raise ValidationError("Invalid phone number format")
    return phone


def validate_idempotency_key(key: Optional[str]) -> Optional[str]:
    """Validate idempotency key format"""
    if key is None:
        return None
    if not re.match(r"^[a-fA-F0-9-]{36}$", key):
        raise ValidationError("Idempotency key must be a valid UUID")
    return key