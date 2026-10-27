"""
API — Управление генерацией Alt-тегов (Модуль 4).
"""
import uuid
import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Project
from app.models.alt_tag import AltTagBatch, ImageAlt
from app.models.pipeline import PipelineRun, ModuleType, RunStatus
from app.schemas.alt_tag import AltTagBatchImportRequest, AltTagBatchResponse, AltTagBatchListResponse
from app.tasks.alt_tag_tasks import process_alt_tag_batch_task

router = APIRouter(prefix="/api/alt-tags", tags=["Alt Tags"])


@router.post("/project/{project_id}/import", response_model=AltTagBatchResponse, status_code=201)
async def import_alt_tags(
    project_id: uuid.UUID,
    data: AltTagBatchImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Импорт списка картинок и старт обработки."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")

    # Создаем пайплайн-ран
    run = PipelineRun(
        project_id=project_id,
        module_type=ModuleType.ALT_TAGS,
        status=RunStatus.PENDING,
        config={"images_count": len(data.images)}
    )
    db.add(run)
    await db.flush()

    # Формируем текстовое описание сайта из приоритетов
    site_desc = ""
    if project.client_priorities and isinstance(project.client_priorities, dict):
        directions = project.client_priorities.get("directions", [])
        if directions:
            site_desc = ", ".join(directions)

    # Создаем батч
    batch = AltTagBatch(
        run_id=run.id,
        project_id=project_id,
        site_description=site_desc,
        total_images=len(data.images)
    )
    db.add(batch)
    await db.flush()

    # Создаем картинки
    images_to_add = []
    for img_data in data.images:
        img_type = "raster"
        src_lower = img_data.image_src.lower()
        if src_lower.endswith(".svg"):
            img_type = "vector"
        elif "icon" in src_lower:
            img_type = "icon"

        image = ImageAlt(
            batch_id=batch.id,
            image_src=img_data.image_src,
            page_url=img_data.page_url,
            original_alt=img_data.original_alt,
            image_type=img_type
        )
        images_to_add.append(image)

    db.add_all(images_to_add)
    await db.commit()
    await db.refresh(batch)

    # Запускаем таску Celery
    process_alt_tag_batch_task.delay(str(batch.id))

    stmt = select(AltTagBatch).options(selectinload(AltTagBatch.images)).where(AltTagBatch.id == batch.id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("/project/{project_id}/batches", response_model=AltTagBatchListResponse)
async def get_project_batches(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Список всех батчей проекта."""
    result = await db.execute(
        select(AltTagBatch)
        .where(AltTagBatch.project_id == project_id)
        .order_by(AltTagBatch.created_at.desc())
    )
    batches = result.scalars().all()
    return AltTagBatchListResponse(items=batches, total=len(batches))


@router.get("/batch/{batch_id}", response_model=AltTagBatchResponse)
async def get_batch_details(batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Детали батча со списком изображений."""
    stmt = select(AltTagBatch).options(selectinload(AltTagBatch.images)).where(AltTagBatch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Батч не найден")
    return batch
