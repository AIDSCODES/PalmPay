"""Health check schemas"""
from pydantic import BaseModel
from typing import Optional


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    model: str
    version: str
    environment: str


class DetailedHealthResponse(HealthCheckResponse):
    """Detailed health check response (admin)"""
    database_pool: Optional[dict] = None
    model_info: Optional[dict] = None
    uptime_seconds: Optional[float] = None