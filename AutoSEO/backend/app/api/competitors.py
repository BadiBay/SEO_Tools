"""
API — Модуль 1: Анализ конкурентов.
Запуск анализа, получение отчётов, управление приоритетами.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.pipeline import PipelineRun, ModuleType
from app.models.competitor import CompetitorReport, Competitor
from app.schemas.project import PipelineRunResponse, PipelineRunDetailResponse, PipelineStepLogResponse
from app.schemas.competitor import (
    CompetitorAnalysisRequest, ClientPrioritiesRequest,
    CompetitorReportResponse, CompetitorResponse,
)
from app.services.pipeline_manager import PipelineManager

router = APIRouter(prefix="/api/competitors", tags=["Competitors"])


@router.post("/priorities")
async def save_priorities(
    data: ClientPrioritiesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Сохранить приоритеты клиента перед запуском анализа."""
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")

    project.client_priorities = {
        "directions": data.directions,
        "top_services": data.top_services,
        "target_audience": data.target_audience,
        "notes": data.notes,
    }
    await db.commit()
    return {"status": "ok", "message": "Приоритеты сохранены"}


@router.post("/analyze", response_model=PipelineRunResponse)
async def start_analysis(
    data: CompetitorAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Запуск полного пайплайна анализа конкурентов."""
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")

    # Создаём запись о запуске
    run = await PipelineManager.create_run(
        project_id=data.project_id,
        module_type=ModuleType.COMPETITORS,
        config=data.config,
        session=db,
    )

    # Запускаем Celery-задачу
    from app.tasks.competitor_tasks import run_competitor_analysis
    run_competitor_analysis.delay(str(run.id), str(data.project_id), data.config)

    return run


@router.get("/reports/{report_id}", response_model=CompetitorReportResponse)
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить отчёт по конкурентам."""
    result = await db.execute(
        select(CompetitorReport).where(CompetitorReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Отчёт не найден")

    # Подгружаем конкурентов
    comps_result = await db.execute(
        select(Competitor).where(Competitor.report_id == report_id)
    )
    competitors = comps_result.scalars().all()

    return CompetitorReportResponse(
        id=report.id,
        run_id=report.run_id,
        project_id=report.project_id,
        created_at=report.created_at,
        competitors=[CompetitorResponse.model_validate(c) for c in competitors],
        marker_queries_count=len(report.marker_queries) if report.marker_queries else 0,
        direct_competitors_count=sum(1 for c in competitors if c.is_direct_competitor),
        total_competitors=len(competitors),
    )


@router.get("/reports/by-run/{run_id}", response_model=CompetitorReportResponse)
async def get_report_by_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить отчёт по ID запуска пайплайна."""
    result = await db.execute(
        select(CompetitorReport).where(CompetitorReport.run_id == run_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Отчёт для данного запуска не найден")

    comps_result = await db.execute(
        select(Competitor).where(Competitor.report_id == report.id)
    )
    competitors = comps_result.scalars().all()

    return CompetitorReportResponse(
        id=report.id,
        run_id=report.run_id,
        project_id=report.project_id,
        created_at=report.created_at,
        competitors=[CompetitorResponse.model_validate(c) for c in competitors],
        marker_queries_count=len(report.marker_queries) if report.marker_queries else 0,
        direct_competitors_count=sum(1 for c in competitors if c.is_direct_competitor),
        total_competitors=len(competitors),
    )
