"""
API — Управление бесплатными ссылками и донорами.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.database import get_db
from app.models.project import Project
from app.models.link import FreeLink, DonorPlatform
from app.schemas.free_link import (
    FreeLinkCreate, FreeLinkResponse, FreeLinkListResponse,
    DonorPlatformCreate, DonorPlatformResponse, DonorPlatformListResponse, FreeLinkVerifyRequest,
    FreeLinkImportRequest
)
from app.tasks.free_link_tasks import generate_free_link_assets_task, verify_free_link_task

router = APIRouter(prefix="/api/free-links", tags=["Free Links"])

# --- Donors ---
@router.get("/donors", response_model=DonorPlatformListResponse)
async def get_donors(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    """Получить список доступных доноров для бесплатного линкбилдинга. Если передан project_id, исключает уже использованные."""
    stmt = select(DonorPlatform).where(DonorPlatform.status == "active")
    
    if project_id:
        # Исключаем доноров, для которых уже есть FreeLink в этом проекте
        subq = select(FreeLink.donor_id).where(FreeLink.project_id == project_id)
        stmt = stmt.where(DonorPlatform.id.not_in(subq))
        
    result = await db.execute(stmt)
    donors = result.scalars().all()
    
    # Если база пуста, добавим несколько моковых для MVP
    if not donors and not project_id:
        mock_donors = [
            DonorPlatform(name="VC.ru", url="https://vc.ru", platform_type="article", requires_logo=True),
            DonorPlatform(name="Пикабу", url="https://pikabu.ru", platform_type="forum"),
            DonorPlatform(name="Habr", url="https://habr.com", platform_type="article"),
            DonorPlatform(name="Yell", url="https://yell.ru", platform_type="directory", requires_logo=True),
            DonorPlatform(name="2GIS", url="https://2gis.ru", platform_type="directory", requires_logo=True),
        ]
        db.add_all(mock_donors)
        await db.commit()
        for d in mock_donors:
            await db.refresh(d)
        donors = mock_donors

    return DonorPlatformListResponse(items=donors, total=len(donors))


@router.post("/donors", response_model=DonorPlatformResponse, status_code=201)
async def create_donor(data: DonorPlatformCreate, db: AsyncSession = Depends(get_db)):
    """Добавить нового донора в базу."""
    donor = DonorPlatform(
        name=data.name,
        url=data.url,
        platform_type=data.platform_type,
        requires_logo=data.requires_logo,
        requires_captcha=data.requires_captcha,
        status="active"
    )
    db.add(donor)
    await db.commit()
    await db.refresh(donor)
    return donor


# --- Free Links ---
@router.post("", response_model=FreeLinkResponse, status_code=201)
async def create_free_link(data: FreeLinkCreate, db: AsyncSession = Depends(get_db)):
    """Создать заявку на бесплатную ссылку (прикрепить к проекту и донору)."""
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
        
    donor = await db.get(DonorPlatform, data.donor_id)
    if not donor:
        raise HTTPException(404, "Донор не найден")

    # Проверка анти-дубль (что на этом доноре еще не размещали для этого проекта)
    existing = await db.execute(
        select(FreeLink).where(
            FreeLink.project_id == data.project_id,
            FreeLink.donor_id == data.donor_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Для этого проекта уже есть задача на доноре {donor.name}")

    link = FreeLink(
        project_id=data.project_id,
        donor_id=data.donor_id,
        target_url=data.target_url,
        status="pending"
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    # Загружаем связи для корректного ответа
    stmt = select(FreeLink).options(selectinload(FreeLink.donor)).where(FreeLink.id == link.id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("/project/{project_id}", response_model=FreeLinkListResponse)
async def get_project_free_links(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Список бесплатных ссылок проекта."""
    result = await db.execute(
        select(FreeLink)
        .options(selectinload(FreeLink.donor))
        .where(FreeLink.project_id == project_id)
        .order_by(FreeLink.created_at.desc())
    )
    links = result.scalars().all()
    return FreeLinkListResponse(items=links, total=len(links))


@router.get("/{link_id}", response_model=FreeLinkResponse)
async def get_free_link(link_id: UUID, db: AsyncSession = Depends(get_db)):
    """Детали бесплатной ссылки."""
    result = await db.execute(
        select(FreeLink)
        .options(selectinload(FreeLink.donor))
        .where(FreeLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    return link


import tldextract

@router.post("/project/{project_id}/import", response_model=dict, status_code=201)
async def import_free_links(project_id: UUID, data: FreeLinkImportRequest, db: AsyncSession = Depends(get_db)):
    """Массовый импорт доноров и исторических ссылок."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
        
    created_donors = 0
    created_links = 0
    
    for item in data.donors:
        ext = tldextract.extract(item.url)
        # Если это нормальный домен (например, sub.domain.com -> domain.com)
        domain = ext.registered_domain if ext.registered_domain else item.url

        # 1. Ищем донора по URL, в котором есть этот корневой домен
        donor_stmt = select(DonorPlatform).where(DonorPlatform.url.ilike(f"%{domain}%"))
        donor_res = await db.execute(donor_stmt)
        donor = donor_res.scalar_one_or_none()
        
        if not donor:
            donor = DonorPlatform(
                name=item.name,
                url=f"https://{domain}" if ext.registered_domain else item.url,
                platform_type=item.platform_type,
                status="active"
            )
            db.add(donor)
            await db.flush()
            created_donors += 1
            
        # 2. Создаем историческую ссылку
        if item.placed_url:
            link_stmt = select(FreeLink).where(FreeLink.project_id == project_id, FreeLink.donor_id == donor.id)
            link_res = await db.execute(link_stmt)
            link = link_res.scalar_one_or_none()
            
            if not link:
                link = FreeLink(
                    project_id=project_id,
                    donor_id=donor.id,
                    target_url=project.domain,
                    placed_url=item.placed_url,
                    status="verified",
                    is_indexed=False,
                    placed_at=datetime.now(timezone.utc)
                )
                db.add(link)
                created_links += 1
                
    await db.commit()
    return {"message": "Импорт завершен", "created_donors": created_donors, "created_links": created_links}


@router.post("/{link_id}/generate", status_code=202)
async def generate_assets(link_id: UUID, db: AsyncSession = Depends(get_db)):
    """Запустить генерацию текста и почты для регистрации."""
    link = await db.get(FreeLink, link_id)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
        
    link.status = "generating"
    await db.commit()
    
    # Запускаем Celery задачу
    generate_free_link_assets_task.delay(str(link.id))
    
    return {"message": "Генерация запущена"}


@router.post("/{link_id}/verify", status_code=202)
async def verify_link(link_id: UUID, data: FreeLinkVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Зафиксировать размещение и запустить проверку доступности и индексации."""
    link = await db.get(FreeLink, link_id)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
        
    link.placed_url = data.placed_url
    link.placed_at = datetime.now(timezone.utc)
    link.status = "verifying"
    await db.commit()
    
    # Запускаем Celery задачу проверки
    verify_free_link_task.delay(str(link.id))
    
    return {"message": "Проверка запущена"}


@router.delete("/{link_id}", status_code=204)
async def delete_free_link(link_id: UUID, db: AsyncSession = Depends(get_db)):
    """Удалить задачу (отменить размещение)."""
    link = await db.get(FreeLink, link_id)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    
    await db.delete(link)
    await db.commit()
    return None
