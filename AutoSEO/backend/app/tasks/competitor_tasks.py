"""
Celery tasks для Модуля 1 — Анализ конкурентов.
Запуск полного пайплайна как фоновой задачи.
"""
import asyncio
import logging
from uuid import UUID

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Запуск async-функции в sync-контексте Celery."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.competitor_tasks.run_competitor_analysis",
    bind=True,
    max_retries=2,
    acks_late=True,
)
def run_competitor_analysis(self, run_id: str, project_id: str, config: dict | None = None):
    """
    Запуск полного пайплайна анализа конкурентов.
    Вызывается из API после создания PipelineRun.
    """
    logger.info(f"Starting competitor analysis: run={run_id}, project={project_id}")

    try:
        from app.services.competitor_pipeline import CompetitorPipeline
        pipeline = CompetitorPipeline(
            run_id=UUID(run_id),
            project_id=UUID(project_id),
            config=config or {},
            celery_task=self,
        )
        _run_async(pipeline.execute())
        logger.info(f"Competitor analysis completed: run={run_id}")

    except Exception as exc:
        logger.error(f"Competitor analysis failed: run={run_id}, error={exc}", exc_info=True)
        # Обновляем статус в БД
        try:
            from app.services.pipeline_manager import PipelineManager
            _run_async(PipelineManager.mark_failed(UUID(run_id), str(exc)))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)
