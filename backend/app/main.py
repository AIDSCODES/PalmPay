"""PalmPay FastAPI Application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AppException, ERROR_CODES
from app.db.database import init_db, close_db, engine
from app.ml.model_loader import initialize_models
from app.api.middleware import RequestIdMiddleware, LoggingMiddleware, SecurityHeadersMiddleware
from app.api.v1 import health, users, biometric, wallets, payments, transactions, devices, admin, business, payment_request, consent, websocket, auth

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Setup logging
    setup_logging()

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Initialize ML models
    try:
        initialize_models()
        logger.info("ML models initialized")
    except Exception as e:
        logger.error(f"ML model initialization failed: {e}")
        # Don't fail startup for model issues in development
        if settings.is_production:
            raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="PalmPay - Palm Vein Biometric Payment System API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Add middleware (order matters - first added = outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"AppException: {exc.code} - {exc.message}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details
                },
                "request_id": request_id
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                },
                "request_id": request_id
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request data",
                    "details": exc.errors()
                },
                "request_id": request_id
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error" if settings.is_production else str(exc)
                },
                "request_id": request_id
            }
        )

    # Include routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(biometric.router, prefix="/api/v1")
    app.include_router(wallets.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(devices.router, prefix="/api/v1")
    app.include_router(business.router, prefix="/api/v1")
    app.include_router(payment_request.router, prefix="/api/v1")
    app.include_router(consent.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "app": "/app",
            "docs": "/docs"
        }

    # Mount frontend static files
    import os
    from fastapi.staticfiles import StaticFiles
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    if os.path.isdir(frontend_dir):
        app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1
    )