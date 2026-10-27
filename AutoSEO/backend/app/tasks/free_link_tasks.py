import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.tasks.celery_app import celery_app

from app.database import async_session_factory
from app.models.link import FreeLink, DonorPlatform
from app.models.project import Project
from app.integrations.llm import get_llm_provider
from app.integrations.alias_manager import AliasManagerAdapter
from app.integrations.indexing_api import IndexingAPIAdapter
from app.integrations.web_scraper import WebScraperAdapter

logger = logging.getLogger(__name__)


async def _generate_free_link_assets_async(link_id: str):
    async with async_session_factory() as db:
        link = await db.get(FreeLink, UUID(link_id))
        if not link:
            return
            
        project = await db.get(Project, link.project_id)
        donor = await db.get(DonorPlatform, link.donor_id)
        
        try:
            # 1. Генерация почты (алиаса)
            alias_adapter = AliasManagerAdapter()
            alias = await alias_adapter.create_alias(project.domain)
            link.email_alias = f"{alias.email}:{alias.password}"
            
            # 2. Генерация промо-текста через LLM
            llm = get_llm_provider("gemini")
            
            prompt = f"""
            Ты - опытный SEO-специалист и PR-менеджер.
            Создай естественный, не слишком рекламный текст для размещения на площадке '{donor.name}' ({donor.platform_type}).
            
            Целевой сайт: {project.domain} ({project.name})
            Продвигаемый URL: {link.target_url}
            
            Требования:
            - Текст должен выглядеть как органичная рекомендация или полезный отзыв от лица обычного пользователя.
            - Объем: 300-500 символов.
            - Естественно вписать ссылку.
            """
            
            promo_text = await llm.generate_text(prompt, max_tokens=1000)
            link.promo_text = promo_text
            
            # Статус: Готов к ручному размещению
            link.status = "ready_for_placement"
            
        except Exception as e:
            logger.error(f"Error generating free link assets: {e}")
            link.status = "error"
            
        finally:
            await db.commit()


@celery_app.task(name="app.tasks.free_link_tasks.generate_free_link_assets")
def generate_free_link_assets_task(link_id: str):
    """Задача генерации промо-текста и email-алиаса для бесплатной ссылки."""
    asyncio.run(_generate_free_link_assets_async(link_id))


async def _verify_free_link_async(link_id: str):
    async with async_session_factory() as db:
        link = await db.get(FreeLink, UUID(link_id))
        if not link or not link.placed_url:
            return
            
        try:
            scraper = WebScraperAdapter()
            is_alive, status_code = await scraper.check_url_alive(link.placed_url)
            
            link.last_http_code = status_code
            import datetime
            from datetime import timezone
            link.last_checked_at = datetime.datetime.now(timezone.utc)
            
            if is_alive:
                link.status = "verified"
                # Отправка в Indexing API
                try:
                    indexer = IndexingAPIAdapter()
                    success = await indexer.submit_url(link.placed_url)
                    if success:
                        link.is_indexed = True
                        link.indexed_at = datetime.datetime.now(timezone.utc)
                except Exception as e:
                    logger.error(f"Indexing API error: {e}")
            else:
                link.status = "dead"
                
        except Exception as e:
            logger.error(f"Error verifying free link: {e}")
            
        finally:
            await db.commit()


@celery_app.task(name="app.tasks.free_link_tasks.verify_free_link")
def verify_free_link_task(link_id: str):
    """Задача проверки размещенной ссылки и отправки в Indexing API."""
    asyncio.run(_verify_free_link_async(link_id))


async def _cron_verify_all_free_links_async():
    async with async_session_factory() as db:
        result = await db.execute(
            select(FreeLink).where(FreeLink.status.in_(["verified", "placed", "dead"]))
        )
        links = result.scalars().all()
        for link in links:
            verify_free_link_task.delay(str(link.id))


@celery_app.task(name="app.tasks.free_link_tasks.cron_verify_all_free_links")
def cron_verify_all_free_links_task():
    """Ежемесячный крон для мониторинга всех размещенных бесплатных ссылок."""
    asyncio.run(_cron_verify_all_free_links_async())
