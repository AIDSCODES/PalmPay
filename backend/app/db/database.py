"""Database configuration and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
    pool_pre_ping=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create tables"""
    try:
        async with engine.begin() as conn:
            # Enable pgvector extension only for PostgreSQL
            if "postgresql" in settings.DATABASE_URL:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


from sqlalchemy import text  # noqa: E402