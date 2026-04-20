"""
PCB Builder - SQLAlchemy Database Engine & Session Management
Uses SQLite for local development when PostgreSQL unavailable.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from shared.config import get_settings

settings = get_settings()

# Check if PostgreSQL is available, fallback to SQLite
DB_URL = os.environ.get("DATABASE_URL", "")

if DB_URL:
    # Use provided PostgreSQL URL
    engine = create_async_engine(
        DB_URL,
        echo=settings.app_debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
else:
    # Use SQLite for local development (no database required)
    engine = create_async_engine(
        "sqlite+aiosqlite:///./pcbbuilder.db",
        echo=settings.app_debug,
        connect_args={"check_same_thread": False},
    )

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
