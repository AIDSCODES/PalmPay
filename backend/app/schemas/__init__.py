"""Schemas package exports"""
from app.schemas.common import (
    BaseResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    PaginationParams,
    PaginatedResponse,
)
from app.schemas.users import (
    UserBase,
    UserCreate,
    UserCreateInternal,
    UserUpdate,
    UserResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    UserListResponse,
)
from app.schemas.biometric import (
    BiometricTemplateBase,
    BiometricTemplateCreate,
    BiometricTemplateResponse,
    BiometricIdentifyRequest,
    BiometricIdentifyResponse,
    BiometricEnrollmentRequest,
    BiometricEnrollmentResponse,
    BiometricQualityCheckResponse,
)
from app.schemas.wallets import (
    WalletBase,
    WalletCreate,
    WalletResponse,
    WalletTopUpRequest,
    WalletBalanceResponse,
)
from app.schemas.transactions import (
    TransactionBase,
    TransactionCreate,
    TransactionResponse,
    PaymentRequest,
    PaymentResponse,
    TransactionFilter,
    TransactionListResponse,
)
from app.schemas.devices import (
    DeviceBase,
    DeviceCreate,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceAuthRequest,
    DeviceResponse,
    DeviceListResponse,
)
from app.schemas.health import (
    HealthCheckResponse,
    DetailedHealthResponse,
)

__all__ = [
    # Common
    "BaseResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "PaginationParams",
    "PaginatedResponse",
    # Users
    "UserBase",
    "UserCreate",
    "UserCreateInternal",
    "UserUpdate",
    "UserResponse",
    "UserRegisterRequest",
    "UserRegisterResponse",
    "UserListResponse",
    # Biometric
    "BiometricTemplateBase",
    "BiometricTemplateCreate",
    "BiometricTemplateResponse",
    "BiometricIdentifyRequest",
    "BiometricIdentifyResponse",
    "BiometricEnrollmentRequest",
    "BiometricEnrollmentResponse",
    "BiometricQualityCheckResponse",
    # Wallets
    "WalletBase",
    "WalletCreate",
    "WalletResponse",
    "WalletTopUpRequest",
    "WalletBalanceResponse",
    # Transactions
    "TransactionBase",
    "TransactionCreate",
    "TransactionResponse",
    "PaymentRequest",
    "PaymentResponse",
    "TransactionFilter",
    "TransactionListResponse",
    # Devices
    "DeviceBase",
    "DeviceCreate",
    "DeviceRegisterRequest",
    "DeviceRegisterResponse",
    "DeviceAuthRequest",
    "DeviceResponse",
    "DeviceListResponse",
    # Health
    "HealthCheckResponse",
    "DetailedHealthResponse",
]