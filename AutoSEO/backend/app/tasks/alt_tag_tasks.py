import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.tasks.celery_app import celery_app

from app.database import async_session_factory
from app.models.alt_tag import AltTagBatch, ImageAlt
from app.models.pipeline import PipelineRun, RunStatus
from app.integrations.llm import get_llm_provider
from app.integrations.web_scraper import WebScraperAdapter

logger = logging.getLogger(__name__)


async def _process_alt_tag_batch_async(batch_id: str):
    async with async_session_factory() as db:
        batch = await db.get(AltTagBatch, UUID(batch_id))
        if not batch:
            return
            
        run = await db.get(PipelineRun, batch.run_id)
        if run:
            run.status = RunStatus.RUNNING
            await db.commit()

        # Получаем все картинки в статусе pending
        result = await db.execute(
            select(ImageAlt).where(ImageAlt.batch_id == batch.id, ImageAlt.status == "pending")
        )
        images = result.scalars().all()
        
        scraper = WebScraperAdapter()
        llm = get_llm_provider("gemini")
        
        for idx, img in enumerate(images):
            try:
                img.status = "processing"
                await db.commit()
                
                # 1. Пропускаем SVG и иконки
                if img.image_type in ["vector", "icon"]:
                    img.status = "skipped"
                    img.error_message = f"Пропущено из-за формата ({img.image_type})"
                    batch.skipped_svg += 1
                    batch.processed_images += 1
                    await db.commit()
                    continue

                # 2. Проверяем старый альт
                if img.original_alt:
                    is_junk = scraper.is_junk_alt(img.original_alt)
                    img.original_alt_is_junk = is_junk
                    # Если есть нормальный старый альт, мы его все равно переписываем? 
                    # По ТЗ: переписываем пустые и мусорные.
                    if not is_junk and len(img.original_alt) > 5:
                        # Альт нормальный, можно не генерировать новый, но по ТЗ 
                        # пользователь загружает картинки, которые ХОЧЕТ обновить.
                        # Допустим, мы все равно генерируем, если прислали.
                        pass
                else:
                    img.original_alt_is_junk = True

                # 3. Достаем H1 со страницы для релевантности (раз пользователь его не шлет)
                page_h1 = ""
                page_title = ""
                if img.page_url and img.page_url.startswith("http"):
                    try:
                        page_content = await scraper.fetch_page(img.page_url)
                        page_h1 = page_content.h1
                        page_title = page_content.title
                        img.page_h1 = page_h1
                        img.page_title = page_title
                    except Exception as e:
                        logger.warning(f"Could not fetch page {img.page_url}: {e}")

                # 4. Обращаемся к Vision модели
                # В ТЗ: 1 предложение общей тематики сайта (мы сохранили в site_description)
                prompt = f"""
                Твоя задача — сгенерировать осмысленный SEO-оптимизированный Alt-тег для этого изображения.
                
                Контекст:
                - Тематика сайта: {batch.site_description or 'Не указана'}
                - H1 страницы, где расположена картинка: {page_h1 or 'Не указан'}
                - Заголовок страницы: {page_title or 'Не указан'}
                
                Правила:
                1. Опиши то, что реально находится на картинке.
                2. Лаконично, максимум 1-2 предложения (не более 120 символов).
                3. Используй ключевые слова, если они уместны и связаны с картинкой.
                4. Выведи ТОЛЬКО текст alt-тега, без кавычек и дополнительных пояснений.
                """
                
                # Задержка 1 сек для rate-limiting
                await asyncio.sleep(1.0)
                
                response = await llm.analyze_image(image_url=img.image_src, prompt=prompt)
                img.generated_alt = response.text.strip().replace('"', '')
                img.status = "done"
                
                # Обновляем прогресс
                batch.processed_images += 1
                if run:
                    percent = int((batch.processed_images / batch.total_images) * 100)
                    run.progress = {
                        "current_step": batch.processed_images,
                        "total_steps": batch.total_images,
                        "percent": percent,
                        "message": f"Обработка изображений ({batch.processed_images}/{batch.total_images})"
                    }
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error processing image {img.id}: {e}")
                img.status = "error"
                img.error_message = str(e)
                batch.processed_images += 1
                await db.commit()
                
        # Батч завершен
        if run:
            run.status = RunStatus.COMPLETED
            import datetime
            from datetime import timezone
            run.completed_at = datetime.datetime.now(timezone.utc)
            run.progress = {
                "current_step": batch.total_images,
                "total_steps": batch.total_images,
                "percent": 100,
                "message": "Обработка завершена"
            }
            await db.commit()


@celery_app.task(name="app.tasks.alt_tag_tasks.process_alt_tag_batch")
def process_alt_tag_batch_task(batch_id: str):
    """Задача пакетной обработки Alt-тегов через Vision модель."""
    asyncio.run(_process_alt_tag_batch_async(batch_id))
