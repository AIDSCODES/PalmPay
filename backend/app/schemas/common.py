"""Common schemas"""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from uuid import UUID


T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    request_id: str


class SuccessResponse(BaseResponse, Generic[T]):
    """Success response model"""
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    """Error detail model"""
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error: ErrorDetail


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )