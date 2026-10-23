"""Custom exceptions"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppException):
    """Input validation error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INVALID_REQUEST", 400, details)


class AuthenticationError(AppException):
    """Authentication error"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "UNAUTHORIZED", 401, details)


class AuthorizationError(AppException):
    """Authorization error"""
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "FORBIDDEN", 403, details)


class NotFoundError(AppException):
    """Resource not found error"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NOT_FOUND", 404, details)


class ConflictError(AppException):
    """Resource conflict error"""
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 409, details)


class RateLimitError(AppException):
    """Rate limit exceeded error"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMITED", 429, details)


class BiometricError(AppException):
    """Biometric processing error"""
    def __init__(self, message: str, code: str = "BIOMETRIC_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 400, details)


class DeviceError(AppException):
    """Device authentication error"""
    def __init__(self, message: str, code: str = "DEVICE_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 401, details)


class WalletError(AppException):
    """Wallet operation error"""
    def __init__(self, message: str, code: str = "WALLET_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 400, details)


class PaymentError(AppException):
    """Payment processing error"""
    def __init__(self, message: str, code: str = "PAYMENT_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, 400, details)


class IdempotencyError(AppException):
    """Idempotency key error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "IDEMPOTENCY_CONFLICT", 409, details)


class ModelError(AppException):
    """ML model error"""
    def __init__(self, message: str = "Model unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MODEL_ERROR", 503, details)


ERROR_CODES = {
    "INVALID_IMAGE": "The provided image is invalid or corrupted",
    "LOW_IMAGE_QUALITY": "Image quality is too low for processing",
    "BIOMETRIC_NO_MATCH": "No matching biometric template found",
    "BIOMETRIC_DUPLICATE": "Biometric template already registered",
    "USER_NOT_FOUND": "User not found",
    "USER_SUSPENDED": "User account is suspended",
    "WALLET_NOT_FOUND": "Wallet not found",
    "INSUFFICIENT_BALANCE": "Insufficient wallet balance",
    "PAYMENT_FAILED": "Payment processing failed",
    "DEVICE_UNAUTHORIZED": "Device authentication failed",
    "DEVICE_REVOKED": "Device has been revoked",
    "INVALID_REQUEST": "Invalid request format or parameters",
    "INTERNAL_ERROR": "Internal server error",
    "UNAUTHORIZED": "Authentication required",
    "FORBIDDEN": "Access denied",
    "NOT_FOUND": "Resource not found",
    "CONFLICT": "Resource conflict",
    "RATE_LIMITED": "Too many requests",
    "BIOMETRIC_ERROR": "Biometric processing error",
    "DEVICE_ERROR": "Device authentication error",
    "WALLET_ERROR": "Wallet operation error",
    "PAYMENT_ERROR": "Payment processing error",
    "IDEMPOTENCY_CONFLICT": "Duplicate request detected",
    "MODEL_ERROR": "ML model unavailable",
}