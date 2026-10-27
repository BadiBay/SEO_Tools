"""
Celery задачи для Модулей 2 и 3 (Бесплатные и платные ссылки).
"""
import asyncio
import logging
from uuid import UUID

from app.tasks.celery_app import celery_app
from app.services.paid_link_pipeline import PaidLinkPipeline

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.link_tasks.generate_paid_link_article")
def generate_paid_link_task(link_id: str, run_id: str):
    """
    Асинхронный запуск пайплайна генерации статьи.
    Мы запускаем asyncio loop, т.к. весь бэкенд и LLM провайдеры асинхронные.
    """
    logger.info(f"Starting PaidLink pipeline for link {link_id}")
    
    async def run_pipeline():
        pipeline = PaidLinkPipeline(link_id=UUID(link_id), run_id=UUID(run_id))
        await pipeline.run()

    asyncio.run(run_pipeline())
