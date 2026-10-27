"""
AutoSEO Platform — Database engine and session management.
Async SQLAlchemy с PostgreSQL через asyncpg.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
import sys
from sqlalchemy.pool import NullPool

is_celery = "celery" in sys.argv[0] or "celery" in sys.modules

engine_kwargs = {
    "echo": settings.app_debug,
}

if is_celery:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """Dependency для FastAPI — создаёт и закрывает сессию.
    
    Сессия НЕ делает auto-commit: эндпоинты должны вызывать
    db.commit() или db.flush() сами для контроля транзакций.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
