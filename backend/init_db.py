"""
PCB Builder - Database Initialization Script
Creates all tables on startup. Safe to run multiple times (idempotent).
"""

import asyncio
import os

from shared.database import engine, Base
from shared.logging_config import logger


async def init_database():
    """Create all database tables if they don't exist."""
    try:
        async with engine.begin() as conn:
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


def init_database_sync():
    """Synchronous wrapper for init_database."""
    asyncio.run(init_database())


if __name__ == "__main__":
    init_database_sync()
