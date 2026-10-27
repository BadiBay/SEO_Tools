"""
AutoSEO Platform — FastAPI Application Entry Point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("autoseo")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения: создание таблиц при старте."""
    logger.info("🚀 AutoSEO Platform starting...")

    # Импортируем все модели для регистрации в metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

    # Load system settings into memory
    from app.database import async_session_factory
    from sqlalchemy import select
    from app.models.system_setting import SystemSetting
    from app.config import settings
    async with async_session_factory() as db:
        res = await db.execute(select(SystemSetting))
        for setting in res.scalars():
            if hasattr(settings, setting.key):
                setattr(settings, setting.key, setting.value)
    logger.info("✅ System settings loaded into memory")

    yield

    await engine.dispose()
    logger.info("🛑 AutoSEO Platform stopped")


# === FastAPI App ===
app = FastAPI(
    title="AutoSEO Platform",
    description="Платформа автоматизации SEO-процессов: анализ конкурентов, линкбилдинг, alt-теги",
    version="0.1.0",
    lifespan=lifespan,
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Роутеры ===
from app.api.projects import router as projects_router
from app.api.competitors import router as competitors_router
from app.api.notifications import router as notifications_router
from app.api.websocket import router as websocket_router
from app.api.paid_links import router as paid_links_router
from app.api.free_links import router as free_links_router
from app.api.alt_tags import router as alt_tags_router
from app.api.settings import router as settings_router

app.include_router(projects_router)
app.include_router(competitors_router)
app.include_router(paid_links_router)
app.include_router(free_links_router)
app.include_router(alt_tags_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(websocket_router)


@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса."""
    return {
        "status": "ok",
        "service": "AutoSEO Platform",
        "version": "0.1.0",
        "llm_provider": settings.default_llm_provider,
    }
