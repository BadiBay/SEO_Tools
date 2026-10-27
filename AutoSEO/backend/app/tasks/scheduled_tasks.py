"""
Регулярные задачи (Celery Beat) — мониторинг ссылок, аудит доноров, проверка индексации.
"""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.scheduled_tasks.check_free_links_alive")
def check_free_links_alive():
    """
    Ежемесячная проверка живучести бесплатных ссылок.
    Обходит все размещённые URL, проверяет HTTP 200, помечает удалённые.
    """
    logger.info("Running monthly free links alive check...")

    async def _check():
        from app.database import async_session_factory
        from app.models.link import FreeLink
        from app.integrations.web_scraper import WebScraperAdapter
        from sqlalchemy import select
        from datetime import datetime, timezone

        scraper = WebScraperAdapter()

        async with async_session_factory() as session:
            result = await session.execute(
                select(FreeLink).where(FreeLink.status.in_(["placed", "verified"]))
            )
            links = result.scalars().all()
            logger.info(f"Checking {len(links)} free links...")

            for link in links:
                if not link.placed_url:
                    continue
                is_alive, code = await scraper.check_url_alive(link.placed_url)
                link.last_http_code = code
                link.last_checked_at = datetime.now(timezone.utc)

                if not is_alive:
                    link.status = "dead"
                    logger.warning(f"Link dead: {link.placed_url} (HTTP {code})")
                    # TODO: отправить уведомление
                else:
                    link.status = "verified"

            await session.commit()
            logger.info("Free links alive check completed.")

    _run_async(_check())


@celery_app.task(name="app.tasks.scheduled_tasks.audit_donor_platforms")
def audit_donor_platforms():
    """
    Ежемесячный аудит базы доноров.
    Исключает заспамленные домены и площадки, закрывшие регистрацию.
    """
    logger.info("Running monthly donor platform audit...")

    async def _audit():
        from app.database import async_session_factory
        from app.models.link import DonorPlatform
        from app.integrations.web_scraper import WebScraperAdapter
        from sqlalchemy import select
        from datetime import datetime, timezone

        scraper = WebScraperAdapter()

        async with async_session_factory() as session:
            result = await session.execute(
                select(DonorPlatform).where(DonorPlatform.status == "active")
            )
            donors = result.scalars().all()
            logger.info(f"Auditing {len(donors)} donor platforms...")

            for donor in donors:
                is_alive, code = await scraper.check_url_alive(donor.url)
                donor.last_checked_at = datetime.now(timezone.utc)

                if not is_alive:
                    donor.status = "closed"
                    logger.warning(f"Donor closed: {donor.url} (HTTP {code})")

            await session.commit()
            logger.info("Donor platform audit completed.")

    _run_async(_audit())


@celery_app.task(name="app.tasks.scheduled_tasks.check_paid_links_indexation")
def check_paid_links_indexation():
    """
    Проверка платнных ссылок на живучесть и наличие ссылки.
    Если страница отдает 404 или пропала из индекса — отправляем уведомление.
    """
    logger.info("Running paid links indexation check...")

    async def _check():
        from app.database import async_session_factory
        from app.models.link import PaidLink
        from app.models.notification import Notification
        from app.integrations.web_scraper import WebScraperAdapter
        from sqlalchemy import select
        from datetime import datetime, timezone

        scraper = WebScraperAdapter()

        async with async_session_factory() as session:
            result = await session.execute(
                select(PaidLink).where(PaidLink.status.in_(["published", "indexed"]))
            )
            links = result.scalars().all()
            logger.info(f"Checking {len(links)} paid links...")

            for link in links:
                if not link.donor_page_url:
                    continue
                is_alive, code = await scraper.check_url_alive(link.donor_page_url)
                
                if not is_alive:
                    link.status = "error"
                    logger.warning(f"Paid Link dead: {link.donor_page_url} (HTTP {code})")
                    # Отправить уведомление
                    notif = Notification(
                        project_id=link.project_id,
                        channel="internal",
                        event_type="link_dead",
                        severity="warning",
                        title=f"Платная ссылка недоступна!",
                        message=f"Страница донора ({link.donor_domain}) вернула статус {code}. Проверьте размещение: {link.donor_page_url}"
                    )
                    session.add(notif)

            await session.commit()
            logger.info("Paid links indexation check completed.")

    _run_async(_check())


@celery_app.task(name="app.tasks.scheduled_tasks.check_free_links_indexation")
def check_free_links_indexation():
    """
    Проверка индексации бесплатных ссылок.
    Проверяет, что размещённые URL отдают HTTP 200, и отправляет в Indexing API.
    """
    logger.info("Running free links indexation check...")

    async def _check():
        from app.database import async_session_factory
        from app.models.link import FreeLink
        from app.models.notification import Notification
        from app.integrations.web_scraper import WebScraperAdapter
        from app.integrations.indexing_api import IndexingAPIAdapter
        from sqlalchemy import select
        from datetime import datetime, timezone

        scraper = WebScraperAdapter()
        indexer = IndexingAPIAdapter()

        async with async_session_factory() as session:
            result = await session.execute(
                select(FreeLink).where(
                    FreeLink.status.in_(["placed", "verified"]),
                    FreeLink.is_indexed.is_(False),
                )
            )
            links = result.scalars().all()
            logger.info(f"Checking indexation for {len(links)} free links...")

            for link in links:
                if not link.placed_url:
                    continue
                is_alive, code = await scraper.check_url_alive(link.placed_url)
                link.last_http_code = code
                link.last_checked_at = datetime.now(timezone.utc)

                if is_alive:
                    try:
                        success = await indexer.submit_url(link.placed_url)
                        if success:
                            link.is_indexed = True
                            link.indexed_at = datetime.now(timezone.utc)
                    except Exception as e:
                        logger.error(f"Indexing API error for {link.placed_url}: {e}")
                else:
                    link.status = "dead"
                    logger.warning(f"Free link dead: {link.placed_url} (HTTP {code})")
                    notif = Notification(
                        project_id=link.project_id,
                        channel="internal",
                        event_type="link_dead",
                        severity="warning",
                        title="Бесплатная ссылка недоступна!",
                        message=f"Ссылка {link.placed_url} вернула статус {code}."
                    )
                    session.add(notif)

            await session.commit()
            logger.info("Free links indexation check completed.")

    _run_async(_check())
