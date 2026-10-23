#!/usr/bin/env python
"""Database initialization script"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import init_db, close_db
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def main():
    """Initialize database"""
    setup_logging()
    logger.info("Initializing database...")

    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())