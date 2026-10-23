"""Health check endpoints"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import settings
from app.schemas.health import HealthCheckResponse, DetailedHealthResponse
from app.ml.embedding import embedding_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Basic health check endpoint"""
    request_id = getattr(request.state, "request_id", "unknown")

    # Check database
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    # Check model
    model_status = "loaded" if embedding_service.model else "not_loaded"

    return HealthCheckResponse(
        status="ok" if db_status == "ok" and model_status == "loaded" else "degraded",
        database=db_status,
        model=model_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse, tags=["Health"])
async def detailed_health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Detailed health check (admin only)"""
    request_id = getattr(request.state, "request_id", "unknown")

    # Check database
    db_status = "ok"
    pool_info = {}
    try:
        await db.execute(text("SELECT 1"))
        # Get pool info if available
        pool_info = {
            "size": "N/A",  # Would need engine reference
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    # Model info
    model_info = {
        "version": embedding_service.model_version,
        "embedding_dim": embedding_service.embedding_dim,
        "type": type(embedding_service.model).__name__
    }

    return DetailedHealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        model="loaded" if embedding_service.model else "not_loaded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database_pool=pool_info,
        model_info=model_info,
        uptime_seconds=None  # Would need app start time
    )