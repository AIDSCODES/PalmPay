"""Middleware"""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import get_logger
from app.core.security import generate_request_id

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add request ID to each request"""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        request.state.request_id = request_id

        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log requests and responses"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(f"Request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"Status: {response.status_code} Duration: {duration:.3f}s"
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url.path} "
                f"Duration: {duration:.3f}s Error: {e}"
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (only in production with HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response