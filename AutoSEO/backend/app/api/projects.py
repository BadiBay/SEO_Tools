"""
API — Управление проектами.
CRUD-операции для центральной сущности «Проект».
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.pipeline import PipelineRun
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectListResponse, PipelineRunResponse,
    ProjectFreeLinksInfoUpdate
)
from app.integrations.web_scraper import WebScraperAdapter

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Создать новый проект. При создании парсит logo/favicon с сайта."""
    # Проверка уникальности домена
    existing = await db.execute(
        select(Project).where(Project.domain == data.domain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Проект для домена {data.domain} уже существует")

    project = Project(
        name=data.name,
        domain=data.domain,
        region=data.region,
        client_priorities=data.client_priorities,
    )
    db.add(project)

    # Парсинг logo/favicon в фоне (не блокируем создание)
    try:
        scraper = WebScraperAdapter()
        page = await scraper.fetch_page(f"https://{data.domain}")
        if page.favicon_url:
            project.favicon_url = page.favicon_url
        if page.logo_url:
            project.client_logo_url = page.logo_url
    except Exception:
        pass  # Не критично — заполнится позже

    from sqlalchemy.exc import IntegrityError

    try:
        await db.commit()
        await db.refresh(project)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, f"Проект для домена {data.domain} уже существует")

    return project

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Список всех проектов."""
    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar()

    result = await db.execute(
        select(Project)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    projects = result.scalars().all()
    return ProjectListResponse(items=projects, total=total)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить проект по ID."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить проект."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.put("/{project_id}/free-links-info", response_model=ProjectResponse)
async def update_project_free_links_info(
    project_id: UUID,
    data: ProjectFreeLinksInfoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить данные проекта для размещения бесплатных ссылок."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
        
    current_priorities = project.client_priorities or {}
    
    current_priorities["free_link_target_url"] = data.target_url
    current_priorities["free_link_promo_text"] = data.promo_text
    current_priorities["free_link_account_data"] = data.account_data
    
    # Чтобы SQLAlchemy понял, что JSONB обновился, нужно переприсвоить
    project.client_priorities = dict(current_priorities)
    
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}/pipeline-runs", response_model=list[PipelineRunResponse])
async def get_project_runs(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Все запуски пайплайнов проекта."""
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.created_at.desc())
    )
    return result.scalars().all()
