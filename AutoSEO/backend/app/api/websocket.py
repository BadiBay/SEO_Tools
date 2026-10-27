"""
API — WebSocket для real-time прогресса пайплайнов.
Клиент подписывается на канал run_id и получает обновления.
"""
import json
import logging
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/runs/{run_id}")
async def pipeline_progress_ws(websocket: WebSocket, run_id: UUID):
    """
    WebSocket endpoint для отслеживания прогресса пайплайна.
    Подписывается на Redis pub/sub канал pipeline:{run_id}.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for run {run_id}")

    try:
        import redis.asyncio as aioredis
        from app.config import settings

        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"pipeline:{run_id}")

        # Отправляем текущий статус из БД
        from app.database import async_session_factory
        from app.models.pipeline import PipelineRun

        async with async_session_factory() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                await websocket.send_json({
                    "run_id": str(run.id),
                    "status": run.status.value if hasattr(run.status, "value") else run.status,
                    "progress": run.progress,
                })

        # Слушаем обновления
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Если пайплайн завершён — закрываем
                if data.get("status") in ("completed", "failed", "cancelled"):
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error for run {run_id}: {e}")
    finally:
        try:
            await pubsub.unsubscribe(f"pipeline:{run_id}")
            await r.close()
        except Exception:
            pass


@router.get("/api/runs/{run_id}")
async def get_run_status(run_id: UUID):
    """Получить статус запуска пайплайна (HTTP fallback для WebSocket)."""
    from app.database import async_session_factory
    from app.models.pipeline import PipelineRun

    async with async_session_factory() as session:
        run = await session.get(PipelineRun, run_id)
        if not run:
            from fastapi import HTTPException
            raise HTTPException(404, "Запуск не найден")

        return {
            "id": str(run.id),
            "project_id": str(run.project_id),
            "module_type": run.module_type.value,
            "status": run.status.value if hasattr(run.status, "value") else run.status,
            "progress": run.progress,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_name": s.step_name,
                    "status": s.status,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "error_message": s.error_message,
                }
                for s in (run.step_logs or [])
            ],
        }
