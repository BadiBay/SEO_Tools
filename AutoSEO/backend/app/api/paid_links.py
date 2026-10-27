"""
API — Управление платными ссылками и генерация статей.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.project import Project
from app.models.link import PaidLink, KeywordCluster, UsedDonor
from app.models.pipeline import PipelineRun
from app.schemas.link import PaidLinkCreate, PaidLinkResponse, PaidLinkListResponse
from app.tasks.link_tasks import generate_paid_link_task

router = APIRouter(prefix="/api/paid-links", tags=["Paid Links"])


@router.post("", response_model=PaidLinkResponse, status_code=201)
async def create_paid_link(data: PaidLinkCreate, db: AsyncSession = Depends(get_db)):
    """Создать заявку на платную ссылку. Проверяет анти-дубль по донорам."""
    # 1. Проверка существования проекта
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")

    # 2. Анти-дубль проверка донора
    existing_donor = await db.execute(
        select(UsedDonor).where(
            UsedDonor.project_id == data.project_id,
            UsedDonor.donor_domain == data.donor_domain
        )
    )
    if existing_donor.scalar_one_or_none():
        raise HTTPException(400, f"Ссылка на доноре {data.donor_domain} уже покупалась для этого проекта!")

    # 3. Найти или создать кластер
    cluster_res = await db.execute(
        select(KeywordCluster).where(
            KeywordCluster.project_id == data.project_id,
            KeywordCluster.main_keyword == data.main_keyword
        )
    )
    cluster = cluster_res.scalar_one_or_none()
    if not cluster:
        cluster = KeywordCluster(
            project_id=data.project_id,
            main_keyword=data.main_keyword,
            landing_page_url=data.landing_page_url
        )
        db.add(cluster)
        await db.flush()

    # 4. Создать PaidLink
    paid_link = PaidLink(
        project_id=data.project_id,
        cluster_id=cluster.id,
        donor_domain=data.donor_domain,
        donor_page_url=data.donor_page_url,
        status="draft"
    )
    db.add(paid_link)
    await db.flush()

    # 5. Записать донора в UsedDonor
    used_donor = UsedDonor(
        project_id=data.project_id,
        donor_domain=data.donor_domain,
        paid_link_id=paid_link.id
    )
    db.add(used_donor)

    try:
        await db.commit()
        await db.refresh(paid_link)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Ошибка уникальности при сохранении донора")

    return paid_link


@router.post("/{link_id}/generate", status_code=202)
async def generate_paid_link_article(link_id: UUID, db: AsyncSession = Depends(get_db)):
    """Запускает пайплайн генерации статьи через Celery."""
    link = await db.get(PaidLink, link_id)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")

    # Создаем запись о запуске пайплайна
    run = PipelineRun(
        project_id=link.project_id,
        module_type="paid_links",
        status="pending"
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Отправляем в Celery
    generate_paid_link_task.delay(str(link.id), str(run.id))

    return {"message": "Генерация запущена", "run_id": run.id}


@router.get("/project/{project_id}", response_model=PaidLinkListResponse)
async def get_project_paid_links(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить список платных ссылок проекта."""
    result = await db.execute(
        select(PaidLink)
        .where(PaidLink.project_id == project_id)
        .order_by(PaidLink.created_at.desc())
    )
    links = result.scalars().all()
    return PaidLinkListResponse(items=links, total=len(links))


@router.get("/{link_id}", response_model=PaidLinkResponse)
async def get_paid_link(link_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить детали платной ссылки."""
    link = await db.get(PaidLink, link_id)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    return link


from app.models.link import DonorPlatform
from app.schemas.free_link import DonorPlatformListResponse
import tldextract
from datetime import datetime, timezone
from app.schemas.link import PaidLinkImportRequest


@router.get("/donors/list", response_model=DonorPlatformListResponse)
async def get_paid_donors(project_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    """Получить список платных доноров (платформы с типом 'paid'). Исключает использованные для проекта."""
    stmt = select(DonorPlatform).where(DonorPlatform.platform_type == "paid", DonorPlatform.status == "active")
    
    if project_id:
        subq = select(UsedDonor.donor_domain).where(UsedDonor.project_id == project_id)
        # donor.url typically stores 'https://domain.com', we need to check if it contains the used domain
        # A simple approach: for each returned donor, we'll filter out in python if it matches used domains
        # Or we just use string matching in SQL.
        used_domains_res = await db.execute(subq)
        used_domains = [d for d in used_domains_res.scalars().all()]
        
        if used_domains:
            # We can't easily exclude by `url NOT LIKE %domain%` for a list of domains in SQL easily, 
            # so we'll filter in Python since the list of paid donors isn't huge.
            pass
            
    result = await db.execute(stmt)
    donors = result.scalars().all()
    
    if project_id and 'used_domains' in locals() and used_domains:
        filtered_donors = []
        for d in donors:
            ext = tldextract.extract(d.url)
            domain = ext.registered_domain if ext.registered_domain else d.url
            if domain not in used_domains:
                filtered_donors.append(d)
        donors = filtered_donors

    return DonorPlatformListResponse(items=donors, total=len(donors))


@router.post("/project/{project_id}/import", response_model=dict, status_code=201)
async def import_paid_links(project_id: UUID, data: PaidLinkImportRequest, db: AsyncSession = Depends(get_db)):
    """Массовый импорт платных ссылок/доноров."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
        
    created_donors = 0
    created_links = 0
    
    for item in data.links:
        ext = tldextract.extract(item.domain)
        domain = ext.registered_domain if ext.registered_domain else item.domain

        # 1. Check/create DonorPlatform
        donor_stmt = select(DonorPlatform).where(DonorPlatform.url.ilike(f"%{domain}%"), DonorPlatform.platform_type == "paid")
        donor_res = await db.execute(donor_stmt)
        donor = donor_res.scalar_one_or_none()
        
        if not donor:
            donor = DonorPlatform(
                name=domain,
                url=f"https://{domain}" if ext.registered_domain else item.domain,
                platform_type="paid",
                status="active"
            )
            db.add(donor)
            await db.flush()
            created_donors += 1
            
        # 2. Check/create UsedDonor
        used_stmt = select(UsedDonor).where(UsedDonor.project_id == project_id, UsedDonor.donor_domain == domain)
        used_res = await db.execute(used_stmt)
        used_donor = used_res.scalar_one_or_none()
        
        if not used_donor:
            # 3. Create PaidLink history
            paid_link = PaidLink(
                project_id=project_id,
                donor_domain=domain,
                donor_page_url=item.placed_url,
                price=item.price,
                miralinks_order_id=item.miralinks_order_id,
                status="published" if item.placed_url else "draft",
                published_at=datetime.now(timezone.utc) if item.placed_url else None
            )
            db.add(paid_link)
            await db.flush()
            created_links += 1
            
            used_donor = UsedDonor(
                project_id=project_id,
                donor_domain=domain,
                paid_link_id=paid_link.id
            )
            db.add(used_donor)

    await db.commit()
    return {"message": "Импорт платных ссылок завершен", "created_donors": created_donors, "created_links": created_links}
