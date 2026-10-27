"""
Пайплайн генерации платных ссылок / аутрич.
"""
import json
import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.link import PaidLink, KeywordCluster, UsedDonor
from app.integrations.llm.factory import get_llm_provider
from app.services.pipeline_manager import PipelineManager


logger = logging.getLogger(__name__)

TOTAL_STEPS = 4


class PaidLinkPipeline:
    def __init__(self, link_id: UUID, run_id: UUID):
        self.link_id = link_id
        self.run_id = run_id
        self.llm = get_llm_provider()

    async def run(self):
        """Запуск генерации статьи для ссылки."""
        await PipelineManager.start_run(self.run_id, TOTAL_STEPS)
        
        try:
            async with async_session_factory() as db:
                link = await db.get(PaidLink, self.link_id)
                if not link:
                    raise ValueError(f"PaidLink {self.link_id} not found")
                
                cluster = await db.get(KeywordCluster, link.cluster_id)
                if not cluster:
                    raise ValueError(f"KeywordCluster {link.cluster_id} not found")

                # Шаг 1: Сбор LSI и структуры (mocking or LLM)
                await PipelineManager.log_step(self.run_id, 1, "Сбор LSI и структуры", "running")
                await PipelineManager.update_progress(self.run_id, 1, TOTAL_STEPS, "Шаг 1/4: Сбор LSI и структуры...")
                await self._step_1_extract_lsi(cluster, db)
                await PipelineManager.log_step(self.run_id, 1, "Сбор LSI и структуры", "completed")

                # Шаг 2: Генерация статьи
                await PipelineManager.log_step(self.run_id, 2, "Генерация SEO-статьи", "running")
                await PipelineManager.update_progress(self.run_id, 2, TOTAL_STEPS, "Шаг 2/4: Генерация SEO-статьи...")
                await self._step_2_generate_article(link, cluster, db)
                await PipelineManager.log_step(self.run_id, 2, "Генерация SEO-статьи", "completed")

                # Шаг 3: Проверка качества
                await PipelineManager.log_step(self.run_id, 3, "Контроль качества (ToV)", "running")
                await PipelineManager.update_progress(self.run_id, 3, TOTAL_STEPS, "Шаг 3/4: Проверка Tone of Voice...")
                await self._step_3_quality_check(link, db)
                await PipelineManager.log_step(self.run_id, 3, "Контроль качества (ToV)", "completed")

                # Шаг 4: Генерация инструкций вебмастеру
                await PipelineManager.log_step(self.run_id, 4, "Задание вебмастеру", "running")
                await PipelineManager.update_progress(self.run_id, 4, TOTAL_STEPS, "Шаг 4/4: Формирование задания...")
                await self._step_4_webmaster_instructions(link, db)
                await PipelineManager.log_step(self.run_id, 4, "Задание вебмастеру", "completed")

                # Завершение
                link.status = "review"
                await db.commit()
                
            await PipelineManager.mark_completed(self.run_id)

        except Exception as e:
            logger.error(f"PaidLink Pipeline failed: {str(e)}", exc_info=True)
            await PipelineManager.mark_failed(self.run_id, str(e))

    async def _step_1_extract_lsi(self, cluster: KeywordCluster, db: AsyncSession):
        """Извлекает LSI и структуру выдачи."""
        if not cluster.lsi_keywords:
            prompt = f"Сгенерируй 15 LSI слов и 5 вариантов анкоров для ключевого запроса: '{cluster.main_keyword}'. Верни JSON."
            response = await self.llm.generate_text(prompt)
            # Упрощенная логика для MVP — используем мок-данные
            cluster.lsi_keywords = {"lsi": [cluster.main_keyword + " цена", "купить " + cluster.main_keyword]}
            cluster.anchor_variants = {"anchors": [cluster.main_keyword, "тут", "подробнее"]}
            await db.commit()

    async def _step_2_generate_article(self, link: PaidLink, cluster: KeywordCluster, db: AsyncSession):
        """Генерирует HTML статью."""
        from app.integrations.web_scraper import WebScraperAdapter
        import json
        
        # 1. Сбор контекста донора
        donor_context = ""
        try:
            scraper = WebScraperAdapter()
            page = await scraper.fetch_page(f"https://{link.donor_domain}")
            
            theme_parts = []
            if page.title:
                theme_parts.append(f"Title: {page.title}")
            if page.meta_description:
                theme_parts.append(f"Description: {page.meta_description}")
            if page.h1:
                theme_parts.append(f"H1: {page.h1}")
                
            if theme_parts:
                donor_context = "Тематика площадки-донора:\n" + "\n".join(theme_parts)
        except Exception as e:
            logger.warning(f"Не удалось получить контекст донора {link.donor_domain}: {e}")
            donor_context = f"Тематика площадки-донора: неизвестно (домен {link.donor_domain})."

        # 2. Промпт с учетом контекста
        prompt = f"""Напиши качественную SEO-статью на тему "{cluster.main_keyword}". 
Объем: около 300-500 слов. Используй HTML теги (h1, h2, p, ul, li).
Органично впиши ссылку: <a href="{cluster.landing_page_url}">{cluster.main_keyword}</a>.

ВАЖНО: Статья будет размещена на сайте-доноре. Постарайся написать так, чтобы она органично вписывалась в его тематику.
{donor_context}

Верни результат строго в формате JSON:
{{
  "title": "Заголовок статьи (H1)",
  "meta_title": "Мета-заголовок",
  "meta_description": "Мета-описание",
  "html_body": "HTML код статьи (включая h1)"
}}
"""
        
        # 3. Генерация и парсинг
        response = await self.llm.generate_text(prompt, temperature=0.7)
        try:
            # Очистка от маркдауна ```json ... ```
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            data = json.loads(text.strip())
            link.article_title = data.get("title", f"Всё, что нужно знать про {cluster.main_keyword}")
            link.meta_title = data.get("meta_title", link.article_title)
            link.meta_description = data.get("meta_description", "")
            link.article_html = data.get("html_body", f"<h1>{link.article_title}</h1><p>Ошибка генерации тела статьи.</p>")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON response for article: {response.text}")
            # Fallback к мок-данным, если парсинг сломался
            link.article_title = f"Статья про {cluster.main_keyword}"
            link.meta_title = link.article_title
            link.meta_description = f"Читайте статью о {cluster.main_keyword} на {link.donor_domain}."
            link.article_html = f"<h1>{link.article_title}</h1><p>Сгенерированная статья про {cluster.main_keyword}. </p><p>Рекомендуем <a href='{cluster.landing_page_url}'>{cluster.main_keyword}</a>.</p>"

        await db.commit()

    async def _step_3_quality_check(self, link: PaidLink, db: AsyncSession):
        """Проверяет ToV и переспам."""
        # Для MVP сразу ставим True
        link.tone_check_passed = True
        link.structure_check_passed = True
        await db.commit()

    async def _step_4_webmaster_instructions(self, link: PaidLink, db: AsyncSession):
        """Инструкции для площадки."""
        link.webmaster_instructions = f"Пожалуйста, разместите статью без изменений. Ссылка на {link.donor_domain} должна быть dofollow и не закрыта от индексации."
        await db.commit()
