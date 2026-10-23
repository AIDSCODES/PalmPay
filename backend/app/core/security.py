"""Security utilities"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import bcrypt
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    pw_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash"""
    try:
        pw_bytes = plain_password.encode('utf-8')[:72]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


def hash_device_key(device_key: str) -> str:
    """Hash a device key for storage (SHA-256)"""
    return hashlib.sha256(device_key.encode()).hexdigest()


def verify_device_key(device_key: str, device_key_hash: str) -> bool:
    """Verify a device key against its hash using constant-time comparison"""
    computed_hash = hash_device_key(device_key)
    return hmac.compare_digest(computed_hash, device_key_hash)


def generate_device_key() -> str:
    """Generate a secure random device key"""
    return secrets.token_urlsafe(32)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return secrets.token_urlsafe(16)


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()