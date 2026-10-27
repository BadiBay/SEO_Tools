"""
Competitor Analysis Pipeline — 14-шаговый пайплайн анализа конкурентов.
Каждый шаг логируется, прогресс публикуется в Redis для real-time UI.
"""
import json
import logging
from uuid import UUID
from collections import Counter
from urllib.parse import urlparse

from sqlalchemy import select

from app.database import async_session_factory
from app.models.project import Project
from app.models.competitor import CompetitorReport, MarkerQuery, Competitor
from app.services.pipeline_manager import PipelineManager
from app.integrations.llm.factory import get_llm_provider, get_vision_provider, get_perplexity_provider
from app.integrations.seo.mock import MockSEOProvider
from app.integrations.serp.parser import MockSERPParser
from app.integrations.web_scraper import WebScraperAdapter
from app.utils.rate_limiter import process_in_batches, RateLimitConfig

logger = logging.getLogger(__name__)

# Агрегаторы/маркетплейсы для автофильтрации
AGGREGATOR_DOMAINS = {
    "ozon.ru", "wildberries.ru", "avito.ru", "yandex.ru", "google.com",
    "market.yandex.ru", "dzen.ru", "youtube.com", "vk.com", "ok.ru",
    "wikipedia.org", "2gis.ru", "zoon.ru", "yell.ru", "irecommend.ru",
    "otzovik.com", "pikabu.ru", "habr.com", "vc.ru",
}

TOTAL_STEPS = 14


class CompetitorPipeline:
    """
    Полный пайплайн анализа конкурентов.

    Шаги:
    1.  Загрузка проекта и приоритетов
    2.  Генерация маркерных запросов через LLM
    3.  Парсинг ТОП-10/50 выдачи
    4.  Дедупликация доменов, исключение агрегаторов
    5.  AI-классификатор: прямой конкурент или нет
    6.  Сбор метрик Keys.so (трафик, видимость, ТОП-запросы)
    7.  Сбор метрик Semrush (DR, беклинки, динамика)
    8.  Анализ тренда видимости (Vision AI)
    9.  Анализ PPC (бюджет, динамика)
    10. Анализ семантики (брендовые/коммерческие/инфо флаги)
    11. Определение возраста домена (WHOIS)
    12. Страницы-лидеры
    13. Анализ УТП через Perplexity
    14. Формирование отчёта
    """

    def __init__(
        self,
        run_id: UUID,
        project_id: UUID,
        config: dict,
        celery_task=None,
    ):
        self.run_id = run_id
        self.project_id = project_id
        self.config = config
        self.celery_task = celery_task

        # Провайдеры (инициализируются лениво)
        self.llm = get_llm_provider()
        self.vision = get_vision_provider()
        self.perplexity = get_perplexity_provider()
        self.seo = MockSEOProvider()  # Заменить на KeysSo/Semrush при наличии ключей
        self.serp = MockSERPParser()
        self.scraper = WebScraperAdapter()

    async def execute(self):
        """Запуск всех шагов пайплайна."""
        await PipelineManager.start_run(self.run_id, TOTAL_STEPS)

        try:
            # 1. Загрузка проекта
            project = await self._step_1_load_project()

            # 2. Генерация маркерных запросов
            queries = await self._step_2_generate_queries(project)

            # 3. Парсинг SERP
            all_serp_results = await self._step_3_parse_serp(queries)

            # 4. Дедупликация и фильтрация
            unique_domains = await self._step_4_deduplicate(all_serp_results, project.domain)

            # 5. AI-классификация
            classified = await self._step_5_classify(unique_domains, project)

            # 6. Метрики Keys.so
            competitors_with_metrics = await self._step_6_seo_metrics(classified)

            # 7. Метрики Semrush
            competitors_with_semrush = await self._step_7_semrush_metrics(competitors_with_metrics)

            # 8. Тренд видимости
            competitors_with_trends = await self._step_8_visibility_trends(competitors_with_semrush)

            # 9. PPC-анализ
            competitors_with_ppc = await self._step_9_ppc_analysis(competitors_with_trends)

            # 10. Семантика
            competitors_with_semantics = await self._step_10_semantic_analysis(competitors_with_ppc)

            # 11. Возраст домена
            competitors_with_age = await self._step_11_domain_age(competitors_with_semantics)

            # 12. Страницы-лидеры
            competitors_with_pages = await self._step_12_top_pages(competitors_with_age)

            # 13. УТП через Perplexity
            competitors_complete = await self._step_13_utp_analysis(competitors_with_pages)

            # 14. Сохранение отчёта
            await self._step_14_save_report(project, queries, competitors_complete)

            await PipelineManager.mark_completed(self.run_id)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            await PipelineManager.mark_failed(self.run_id, str(e))
            raise

    # ========================
    # Шаги пайплайна
    # ========================

    async def _step_1_load_project(self) -> Project:
        """Шаг 1: Загрузка проекта и проверка приоритетов."""
        await PipelineManager.log_step(self.run_id, 1, "Загрузка проекта", "running")
        await PipelineManager.update_progress(self.run_id, 1, TOTAL_STEPS, "Загрузка данных проекта...")

        async with async_session_factory() as session:
            project = await session.get(Project, self.project_id)
            if not project:
                raise ValueError(f"Проект {self.project_id} не найден")

            await PipelineManager.log_step(
                self.run_id, 1, "Загрузка проекта", "completed",
                output_data={"domain": project.domain, "has_priorities": bool(project.client_priorities)}
            )
            return project

    async def _step_2_generate_queries(self, project: Project) -> list[dict]:
        """Шаг 2: Генерация маркерных запросов через LLM по приоритетам клиента."""
        await PipelineManager.log_step(self.run_id, 2, "Генерация маркерных запросов", "running")
        await PipelineManager.update_progress(self.run_id, 2, TOTAL_STEPS, "Генерация маркерных запросов через AI...")

        priorities = project.client_priorities or {}
        directions = priorities.get("directions", [project.domain])

        prompt = f"""Ты SEO-аналитик. Сгенерируй 10-15 маркерных поисковых запросов для поиска конкурентов сайта {project.domain}.

Регион: {project.region or 'Россия'}
Основные направления бизнеса: {', '.join(directions)}

Требования к запросам:
- Коммерческие запросы (с интентом покупки/заказа)
- Разнообразие: общие, средне- и низкочастотные
- По каждому маржинальному направлению — минимум 2-3 запроса
- Без брендовых запросов

Верни JSON-массив строк. Только JSON, без пояснений."""

        response = await self.llm.generate_text(prompt, system_prompt="Отвечай только валидным JSON.")

        try:
            queries_text = json.loads(response.text)
        except json.JSONDecodeError:
            queries_text = [q.strip() for q in response.text.split("\n") if q.strip()]

        queries = []
        search_engines = self.config.get("search_engines", ["google"])

        for q in queries_text[:15]:
            for se in search_engines:
                queries.append({"query": q, "search_engine": se, "direction": directions[0] if directions else ""})

        await PipelineManager.log_step(
            self.run_id, 2, "Генерация маркерных запросов", "completed",
            output_data={"queries_count": len(queries), "sample": queries[:3]}
        )
        return queries

    async def _step_3_parse_serp(self, queries: list[dict]) -> list[dict]:
        """Шаг 3: Парсинг выдачи по всем запросам."""
        await PipelineManager.log_step(self.run_id, 3, "Парсинг поисковой выдачи", "running")
        await PipelineManager.update_progress(self.run_id, 3, TOTAL_STEPS, "Парсинг ТОП-10 выдачи...")

        top_depth = self.config.get("top_depth", 10)
        all_results = []

        async def parse_one(query_info):
            results = await self.serp.parse_serp(
                query=query_info["query"],
                search_engine=query_info["search_engine"],
                top_n=top_depth,
            )
            return {"query": query_info, "results": results}

        batch_results = await process_in_batches(
            queries, parse_one,
            RateLimitConfig(delay_seconds=0.7, batch_size=5),
        )

        for r in batch_results:
            if not isinstance(r, Exception):
                all_results.append(r)

        await PipelineManager.log_step(
            self.run_id, 3, "Парсинг поисковой выдачи", "completed",
            output_data={"total_results": sum(len(r["results"]) for r in all_results)}
        )
        return all_results

    async def _step_4_deduplicate(self, serp_results: list[dict], own_domain: str) -> list[str]:
        """Шаг 4: Дедупликация доменов и исключение агрегаторов/маркетплейсов."""
        await PipelineManager.log_step(self.run_id, 4, "Дедупликация и фильтрация", "running")
        await PipelineManager.update_progress(self.run_id, 4, TOTAL_STEPS, "Фильтрация агрегаторов и дублей...")

        domain_counter = Counter()

        for item in serp_results:
            for result in item["results"]:
                domain = result.domain.lower().replace("www.", "")
                domain_counter[domain] += 1

        # Фильтрация
        own = own_domain.lower().replace("www.", "")
        filtered = []
        excluded = []

        for domain, count in domain_counter.most_common():
            if domain == own:
                continue
            if domain in AGGREGATOR_DOMAINS:
                excluded.append(domain)
                continue
            # Домен в ТОПе хотя бы по 2 запросам — более вероятный конкурент
            if count >= 1:
                filtered.append(domain)

        max_competitors = self.config.get("max_competitors", 15)
        unique_domains = filtered[:max_competitors]

        await PipelineManager.log_step(
            self.run_id, 4, "Дедупликация и фильтрация", "completed",
            output_data={
                "total_unique": len(filtered),
                "excluded_aggregators": excluded,
                "selected": len(unique_domains),
            }
        )
        return unique_domains

    async def _step_5_classify(self, domains: list[str], project: Project) -> list[dict]:
        """Шаг 5: AI-классификатор — сканирование главной страницы + бинарный вердикт."""
        await PipelineManager.log_step(self.run_id, 5, "AI-классификация конкурентов", "running")
        await PipelineManager.update_progress(self.run_id, 5, TOTAL_STEPS, "Классификация конкурентов через AI...")

        results = []

        async def classify_one(domain):
            try:
                page = await self.scraper.fetch_page(f"https://{domain}")
                content_snippet = page.text_content[:1500] if page.text_content else ""

                prompt = f"""Проанализируй, является ли сайт {domain} прямым конкурентом для {project.domain}.

Тематика анализируемого бизнеса: {project.site_description or project.name}
Направления: {json.dumps(project.client_priorities.get('directions', []) if project.client_priorities else [], ensure_ascii=False)}

Контент главной страницы {domain}:
{content_snippet}

Ответь строго JSON: {{"is_competitor": true/false, "reason": "краткое обоснование", "confidence": 0.0-1.0}}"""

                response = await self.llm.generate_text(prompt, system_prompt="Отвечай только валидным JSON.")

                try:
                    verdict = json.loads(response.text)
                except json.JSONDecodeError:
                    verdict = {"is_competitor": True, "reason": "Не удалось распарсить ответ AI", "confidence": 0.5}

                return {
                    "domain": domain,
                    "is_competitor": verdict.get("is_competitor", True),
                    "reason": verdict.get("reason", ""),
                    "confidence": verdict.get("confidence", 0.5),
                    "page_title": page.title,
                }
            except Exception as e:
                logger.warning(f"Classification failed for {domain}: {e}")
                return {
                    "domain": domain,
                    "is_competitor": True,  # Если не смогли классифицировать — включаем
                    "reason": f"Ошибка классификации: {str(e)[:100]}",
                    "confidence": 0.3,
                }

        batch_results = await process_in_batches(
            domains, classify_one,
            RateLimitConfig(delay_seconds=1.0, batch_size=3),
        )

        for r in batch_results:
            if not isinstance(r, Exception):
                results.append(r)

        await PipelineManager.log_step(
            self.run_id, 5, "AI-классификация конкурентов", "completed",
            output_data={
                "total": len(results),
                "direct_competitors": sum(1 for r in results if r["is_competitor"]),
            }
        )
        return results

    async def _step_6_seo_metrics(self, classified: list[dict]) -> list[dict]:
        """Шаг 6: Сбор метрик через Keys.so/Mock."""
        await PipelineManager.log_step(self.run_id, 6, "Сбор SEO-метрик (Keys.so)", "running")
        await PipelineManager.update_progress(self.run_id, 6, TOTAL_STEPS, "Сбор SEO-метрик...")

        async def fetch_metrics(comp):
            metrics = await self.seo.get_domain_metrics(comp["domain"])
            comp["traffic"] = metrics.traffic
            comp["visibility"] = metrics.visibility
            comp["top10_count"] = metrics.top10_count
            comp["top50_count"] = metrics.top50_count
            return comp

        results = await process_in_batches(
            classified, fetch_metrics,
            RateLimitConfig(delay_seconds=0.5, batch_size=5),
        )

        valid = [r for r in results if not isinstance(r, Exception)]
        await PipelineManager.log_step(self.run_id, 6, "Сбор SEO-метрик (Keys.so)", "completed",
                                        output_data={"collected": len(valid)})
        return valid

    async def _step_7_semrush_metrics(self, competitors: list[dict]) -> list[dict]:
        """Шаг 7: Semrush — DR, беклинки, динамика ссылочной массы."""
        await PipelineManager.log_step(self.run_id, 7, "Сбор метрик Semrush", "running")
        await PipelineManager.update_progress(self.run_id, 7, TOTAL_STEPS, "Semrush: DR, беклинки...")

        async def fetch_semrush(comp):
            metrics = await self.seo.get_domain_metrics(comp["domain"])
            comp["semrush_dr"] = metrics.domain_rating
            comp["semrush_backlinks"] = metrics.backlinks_count
            comp["semrush_link_trend"] = metrics.link_trend
            return comp

        results = await process_in_batches(
            competitors, fetch_semrush,
            RateLimitConfig(delay_seconds=0.5, batch_size=5),
        )

        valid = [r for r in results if not isinstance(r, Exception)]
        await PipelineManager.log_step(self.run_id, 7, "Сбор метрик Semrush", "completed",
                                        output_data={"collected": len(valid)})
        return valid

    async def _step_8_visibility_trends(self, competitors: list[dict]) -> list[dict]:
        """Шаг 8: Тренд видимости через Vision AI."""
        await PipelineManager.log_step(self.run_id, 8, "Анализ трендов видимости", "running")
        await PipelineManager.update_progress(self.run_id, 8, TOTAL_STEPS, "Анализ трендов видимости...")

        async def analyze_trend(comp):
            history = await self.seo.get_visibility_history(comp["domain"])

            if len(history) >= 3:
                first_half_avg = sum(p.visibility for p in history[:len(history)//2]) / max(len(history)//2, 1)
                second_half_avg = sum(p.visibility for p in history[len(history)//2:]) / max(len(history) - len(history)//2, 1)

                if second_half_avg > first_half_avg * 1.15:
                    trend, color = "growth", "green"
                elif second_half_avg < first_half_avg * 0.85:
                    trend, color = "decline", "red"
                else:
                    trend, color = "stagnation", "yellow"
            else:
                trend, color = "stagnation", "yellow"

            comp["visibility_trend"] = trend
            comp["visibility_color"] = color
            return comp

        results = await process_in_batches(
            competitors, analyze_trend,
            RateLimitConfig(delay_seconds=0.3, batch_size=5),
        )

        valid = [r for r in results if not isinstance(r, Exception)]
        await PipelineManager.log_step(self.run_id, 8, "Анализ трендов видимости", "completed",
                                        output_data={"analyzed": len(valid)})
        return valid

    async def _step_9_ppc_analysis(self, competitors: list[dict]) -> list[dict]:
        """Шаг 9: PPC — наличие рекламы, бюджет, динамика."""
        await PipelineManager.log_step(self.run_id, 9, "Анализ контекстной рекламы", "running")
        await PipelineManager.update_progress(self.run_id, 9, TOTAL_STEPS, "Анализ PPC конкурентов...")

        async def analyze_ppc(comp):
            metrics = await self.seo.get_domain_metrics(comp["domain"])
            comp["has_ppc"] = metrics.has_ppc
            comp["ppc_budget"] = metrics.ppc_budget
            comp["ppc_budget_trend"] = metrics.ppc_budget_trend
            return comp

        results = await process_in_batches(competitors, analyze_ppc, RateLimitConfig(delay_seconds=0.3, batch_size=5))
        valid = [r for r in results if not isinstance(r, Exception)]

        await PipelineManager.log_step(self.run_id, 9, "Анализ контекстной рекламы", "completed",
                                        output_data={"with_ppc": sum(1 for r in valid if r.get("has_ppc"))})
        return valid

    async def _step_10_semantic_analysis(self, competitors: list[dict]) -> list[dict]:
        """Шаг 10: Анализ семантики — брендовые/коммерческие/инфо запросы."""
        await PipelineManager.log_step(self.run_id, 10, "Анализ семантики", "running")
        await PipelineManager.update_progress(self.run_id, 10, TOTAL_STEPS, "Анализ структуры семантики...")

        async def analyze_semantics(comp):
            keywords = await self.seo.get_keywords(comp["domain"], limit=50)

            brand_count = sum(1 for k in keywords if k.keyword_type == "brand")
            commercial_count = sum(1 for k in keywords if k.keyword_type == "commercial")
            info_count = sum(1 for k in keywords if k.keyword_type == "info")
            total = len(keywords)

            comp["has_brand_queries"] = brand_count > 0
            comp["has_commercial_queries"] = commercial_count > 0
            comp["has_info_queries"] = info_count > 0
            comp["semantic_structure"] = {
                "brand": brand_count,
                "commercial": commercial_count,
                "info": info_count,
                "total": total,
                "brand_pct": round(brand_count / max(total, 1) * 100, 1),
                "commercial_pct": round(commercial_count / max(total, 1) * 100, 1),
            }
            return comp

        results = await process_in_batches(competitors, analyze_semantics, RateLimitConfig(delay_seconds=0.3, batch_size=5))
        valid = [r for r in results if not isinstance(r, Exception)]

        await PipelineManager.log_step(self.run_id, 10, "Анализ семантики", "completed",
                                        output_data={"analyzed": len(valid)})
        return valid

    async def _step_11_domain_age(self, competitors: list[dict]) -> list[dict]:
        """Шаг 11: Определение возраста домена через WHOIS."""
        await PipelineManager.log_step(self.run_id, 11, "Определение возраста доменов", "running")
        await PipelineManager.update_progress(self.run_id, 11, TOTAL_STEPS, "WHOIS: возраст доменов...")

        async def get_age(comp):
            age = await self.scraper.get_domain_age(comp["domain"])
            comp["domain_age_years"] = age
            return comp

        results = await process_in_batches(competitors, get_age, RateLimitConfig(delay_seconds=1.0, batch_size=3))
        valid = [r for r in results if not isinstance(r, Exception)]

        await PipelineManager.log_step(self.run_id, 11, "Определение возраста доменов", "completed",
                                        output_data={"analyzed": len(valid)})
        return valid

    async def _step_12_top_pages(self, competitors: list[dict]) -> list[dict]:
        """Шаг 12: Страницы-лидеры — что именно генерирует трафик."""
        await PipelineManager.log_step(self.run_id, 12, "Анализ страниц-лидеров", "running")
        await PipelineManager.update_progress(self.run_id, 12, TOTAL_STEPS, "Страницы-лидеры конкурентов...")

        async def get_top(comp):
            pages = await self.seo.get_top_pages(comp["domain"], limit=10)
            comp["top_pages"] = [
                {
                    "url": p.url,
                    "traffic": p.traffic,
                    "traffic_share": p.traffic_share,
                    "keywords_count": p.keywords_count,
                    "page_type": p.page_type,
                }
                for p in pages
            ]
            return comp

        results = await process_in_batches(competitors, get_top, RateLimitConfig(delay_seconds=0.5, batch_size=5))
        valid = [r for r in results if not isinstance(r, Exception)]

        await PipelineManager.log_step(self.run_id, 12, "Анализ страниц-лидеров", "completed",
                                        output_data={"analyzed": len(valid)})
        return valid

    async def _step_13_utp_analysis(self, competitors: list[dict]) -> list[dict]:
        """Шаг 13: Анализ УТП и структуры через Perplexity (web-search)."""
        await PipelineManager.log_step(self.run_id, 13, "Анализ УТП (Perplexity)", "running")
        await PipelineManager.update_progress(self.run_id, 13, TOTAL_STEPS, "Perplexity: анализ УТП конкурентов...")

        async def analyze_utp(comp):
            prompt = f"""Проанализируй сайт {comp['domain']} и ответь на вопросы:

1. Назови 3 главных УТП (уникальных торговых предложения) этой компании.
2. Перечисли основные категории из меню навигации сайта (для оценки ширины ассортимента).
3. На какие типы страниц (услуги/каталог/статьи/лендинги) сделан основной акцент?

Ответ строго в формате JSON:
{{"utps": ["УТП 1", "УТП 2", "УТП 3"], "categories": ["Категория 1", ...], "main_focus": "описание акцента"}}"""

            response = await self.perplexity.search_and_analyze(
                prompt,
                system_prompt="Ты SEO-аналитик. Анализируй реальный контент сайтов. Отвечай только валидным JSON."
            )

            try:
                comp["utp_analysis"] = json.loads(response.text)
            except json.JSONDecodeError:
                comp["utp_analysis"] = {"raw_text": response.text[:500]}

            return comp

        # Perplexity дороже — меньше батч, больше задержка
        results = await process_in_batches(
            competitors, analyze_utp,
            RateLimitConfig(delay_seconds=2.0, batch_size=2),
        )

        valid = [r for r in results if not isinstance(r, Exception)]
        await PipelineManager.log_step(self.run_id, 13, "Анализ УТП (Perplexity)", "completed",
                                        output_data={"analyzed": len(valid)})
        return valid

    async def _step_14_save_report(self, project: Project, queries: list[dict], competitors_data: list[dict]):
        """Шаг 14: Сохранение отчёта в БД."""
        await PipelineManager.log_step(self.run_id, 14, "Сохранение отчёта", "running")
        await PipelineManager.update_progress(self.run_id, 14, TOTAL_STEPS, "Сохранение отчёта в БД...")

        async with async_session_factory() as session:
            # Создаём отчёт
            report = CompetitorReport(
                run_id=self.run_id,
                project_id=self.project_id,
            )
            session.add(report)
            await session.flush()

            # Сохраняем маркерные запросы
            for q in queries:
                mq = MarkerQuery(
                    report_id=report.id,
                    query_text=q["query"],
                    priority_direction=q.get("direction", ""),
                    search_engine=q.get("search_engine", "google"),
                )
                session.add(mq)

            # Сохраняем конкурентов
            for comp in competitors_data:
                competitor = Competitor(
                    report_id=report.id,
                    domain=comp["domain"],
                    is_direct_competitor=comp.get("is_competitor"),
                    ai_classification_reason=comp.get("reason"),
                    traffic_keys_so=comp.get("traffic"),
                    visibility_keys_so=comp.get("visibility"),
                    top10_count=comp.get("top10_count"),
                    top50_count=comp.get("top50_count"),
                    visibility_trend=comp.get("visibility_trend"),
                    visibility_color=comp.get("visibility_color"),
                    has_ppc=comp.get("has_ppc"),
                    ppc_budget_estimate=comp.get("ppc_budget"),
                    ppc_budget_trend=comp.get("ppc_budget_trend"),
                    has_brand_queries=comp.get("has_brand_queries"),
                    has_commercial_queries=comp.get("has_commercial_queries"),
                    has_info_queries=comp.get("has_info_queries"),
                    domain_age_years=comp.get("domain_age_years"),
                    semrush_domain_rating=comp.get("semrush_dr"),
                    semrush_backlinks_count=comp.get("semrush_backlinks"),
                    semrush_link_trend=comp.get("semrush_link_trend"),
                    top_pages=comp.get("top_pages"),
                    utp_analysis=comp.get("utp_analysis"),
                    semantic_structure=comp.get("semantic_structure"),
                    raw_metrics=comp.get("raw_metrics"),
                )
                session.add(competitor)

            await session.commit()

            await PipelineManager.log_step(
                self.run_id, 14, "Сохранение отчёта", "completed",
                output_data={
                    "report_id": str(report.id),
                    "queries_count": len(queries),
                    "competitors_count": len(competitors_data),
                    "direct_competitors": sum(1 for c in competitors_data if c.get("is_competitor")),
                }
            )
