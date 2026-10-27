"""
Pipeline Manager — управление запусками пайплайнов.
Создание, обновление статуса, логирование шагов, публикация прогресса в Redis (для WebSocket).
"""
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.pipeline import PipelineRun, PipelineStepLog, RunStatus, ModuleType

logger = logging.getLogger(__name__)


class PipelineManager:
    """Управление жизненным циклом запуска пайплайна."""

    @staticmethod
    async def create_run(
        project_id: UUID,
        module_type: ModuleType,
        config: dict | None = None,
        session: AsyncSession | None = None,
    ) -> PipelineRun:
        """Создать новый запуск пайплайна."""
        own_session = session is None
        if own_session:
            session = async_session_factory()

        try:
            run = PipelineRun(
                project_id=project_id,
                module_type=module_type,
                status=RunStatus.PENDING,
                config=config,
                progress={"current_step": 0, "total_steps": 0, "percent": 0, "message": "Инициализация..."},
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            logger.info(f"Created pipeline run {run.id} for project {project_id}, module {module_type.value}")
            return run
        finally:
            if own_session:
                await session.close()

    @staticmethod
    async def start_run(run_id: UUID, total_steps: int):
        """Пометить запуск как начавшийся."""
        async with async_session_factory() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                run.status = RunStatus.RUNNING
                run.started_at = datetime.now(timezone.utc)
                run.progress = {
                    "current_step": 0,
                    "total_steps": total_steps,
                    "percent": 0,
                    "message": "Запуск пайплайна...",
                }
                await session.commit()
                await PipelineManager._publish_progress(run)

    @staticmethod
    async def update_progress(run_id: UUID, step: int, total: int, message: str):
        """Обновить прогресс запуска."""
        async with async_session_factory() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                percent = round((step / total) * 100) if total > 0 else 0
                run.progress = {
                    "current_step": step,
                    "total_steps": total,
                    "percent": percent,
                    "message": message,
                }
                await session.commit()
                await PipelineManager._publish_progress(run)

    @staticmethod
    async def log_step(
        run_id: UUID,
        step_number: int,
        step_name: str,
        status: str = "running",
        input_data: dict | None = None,
        output_data: dict | None = None,
        error_message: str | None = None,
    ) -> PipelineStepLog:
        """Записать или обновить лог шага."""
        async with async_session_factory() as session:
            # Поищем существующий лог этого шага
            result = await session.execute(
                select(PipelineStepLog).where(
                    PipelineStepLog.run_id == run_id,
                    PipelineStepLog.step_number == step_number,
                )
            )
            step_log = result.scalar_one_or_none()

            if step_log:
                step_log.status = status
                if output_data:
                    step_log.output_data = output_data
                if error_message:
                    step_log.error_message = error_message
                if status == "running":
                    step_log.started_at = datetime.now(timezone.utc)
                elif status in ("completed", "failed"):
                    step_log.completed_at = datetime.now(timezone.utc)
            else:
                step_log = PipelineStepLog(
                    run_id=run_id,
                    step_number=step_number,
                    step_name=step_name,
                    status=status,
                    input_data=input_data,
                    started_at=datetime.now(timezone.utc) if status == "running" else None,
                )
                session.add(step_log)

            await session.commit()
            await session.refresh(step_log)
            return step_log

    @staticmethod
    async def mark_completed(run_id: UUID):
        """Пометить запуск как завершённый."""
        async with async_session_factory() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)
                if run.progress:
                    updated = dict(run.progress)
                    updated["percent"] = 100
                    updated["message"] = "Анализ завершён"
                    run.progress = updated
                    
                # Create notification
                from app.models.notification import Notification
                notif = Notification(
                    project_id=run.project_id,
                    channel="internal",
                    event_type="pipeline_completed",
                    severity="info",
                    title=f"Анализ завершен",
                    message=f"Пайплайн модуля {run.module_type.value} успешно завершен."
                )
                session.add(notif)
                
                await session.commit()
                await PipelineManager._publish_progress(run)

    @staticmethod
    async def mark_failed(run_id: UUID, error: str):
        """Пометить запуск как проваленный."""
        async with async_session_factory() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = error
                if run.progress:
                    updated = dict(run.progress)
                    updated["message"] = f"Ошибка: {error[:200]}"
                    run.progress = updated
                    
                # Create notification
                from app.models.notification import Notification
                notif = Notification(
                    project_id=run.project_id,
                    channel="internal",
                    event_type="pipeline_failed",
                    severity="critical",
                    title=f"Ошибка в пайплайне",
                    message=f"Пайплайн модуля {run.module_type.value} завершился с ошибкой: {error[:200]}"
                )
                session.add(notif)
                
                await session.commit()
                await PipelineManager._publish_progress(run)

    @staticmethod
    async def _publish_progress(run: PipelineRun):
        """Опубликовать прогресс в Redis pub/sub для WebSocket."""
        try:
            import redis.asyncio as aioredis
            from app.config import settings

            async with aioredis.from_url(settings.redis_url) as r:
                message = json.dumps({
                    "run_id": str(run.id),
                    "status": run.status.value if hasattr(run.status, "value") else run.status,
                    "progress": run.progress,
                }, ensure_ascii=False)
                await r.publish(f"pipeline:{run.id}", message)
        except Exception as e:
            logger.debug(f"Could not publish progress to Redis: {e}")

