"""
Mock SEO Metrics Provider — заглушка для разработки.
Возвращает реалистичные тестовые данные по SEO-метрикам доменов.
"""
import random
from datetime import datetime, timedelta
from app.integrations.base import (
    BaseSEOMetricsProvider,
    DomainMetrics,
    VisibilityPoint,
    PageMetrics,
    KeywordInfo,
)


class MockSEOProvider(BaseSEOMetricsProvider):
    """Заглушка SEO-провайдера с реалистичными данными."""

    async def get_domain_metrics(self, domain: str) -> DomainMetrics:
        seed = hash(domain) % 1000
        random.seed(seed)

        traffic = random.randint(500, 150000)
        return DomainMetrics(
            domain=domain,
            traffic=float(traffic),
            visibility=random.randint(100, 50000),
            top10_count=random.randint(10, 500),
            top50_count=random.randint(50, 2000),
            domain_rating=round(random.uniform(10, 80), 1),
            backlinks_count=random.randint(100, 50000),
            referring_domains=random.randint(20, 5000),
            has_ppc=random.choice([True, False]),
            ppc_budget=round(random.uniform(0, 500000), 0) if random.random() > 0.3 else None,
            ppc_budget_trend=random.choice(["growing", "stable", "declining"]),
            link_trend=random.choice(["growing", "stable", "declining"]),
            raw={"provider": "mock", "seed": seed},
        )

    async def get_visibility_history(self, domain: str, months: int = 12) -> list[VisibilityPoint]:
        seed = hash(domain) % 1000
        random.seed(seed)

        base = random.randint(500, 10000)
        trend = random.choice([-50, 0, 0, 50, 100])  # bias towards growth/stable
        points = []

        now = datetime.now()
        for i in range(months):
            date = now - timedelta(days=30 * (months - i))
            val = max(0, base + trend * i + random.randint(-200, 200))
            points.append(VisibilityPoint(
                date=date.strftime("%Y-%m-%d"),
                visibility=float(val),
            ))

        return points

    async def get_top_pages(self, domain: str, limit: int = 20) -> list[PageMetrics]:
        seed = hash(domain) % 1000
        random.seed(seed)

        page_types = [
            ("/", "main", 0.15),
            ("/catalog", "commercial", 0.25),
            ("/catalog/okna-pvh", "commercial", 0.12),
            ("/catalog/dveri", "commercial", 0.08),
            ("/prices", "commercial", 0.10),
            ("/blog", "info", 0.05),
            ("/blog/kak-vybrat-okna", "info", 0.04),
            ("/about", "info", 0.03),
            ("/contacts", "info", 0.02),
            ("/calculator", "commercial", 0.06),
        ]

        total_traffic = random.randint(5000, 100000)
        pages = []
        for url, ptype, share in page_types[:limit]:
            pages.append(PageMetrics(
                url=f"https://{domain}{url}",
                traffic=round(total_traffic * share),
                traffic_share=round(share * 100, 1),
                keywords_count=random.randint(5, 200),
                page_type=ptype,
            ))

        return pages

    async def get_keywords(self, domain: str, limit: int = 100) -> list[KeywordInfo]:
        seed = hash(domain) % 1000
        random.seed(seed)

        sample_keywords = [
            ("окна пвх", "commercial", 12000),
            ("пластиковые окна", "commercial", 18000),
            ("купить окна", "commercial", 8000),
            (f"{domain.split('.')[0]}", "brand", 2000),
            (f"{domain.split('.')[0]} отзывы", "brand", 500),
            ("как выбрать пластиковые окна", "info", 4000),
            ("окна цена москва", "commercial", 6000),
            ("установка окон", "commercial", 3500),
            ("остекление балкона", "commercial", 5000),
            ("энергосберегающие окна", "info", 2500),
        ]

        keywords = []
        for kw, ktype, volume in sample_keywords[:limit]:
            keywords.append(KeywordInfo(
                keyword=kw,
                position=random.randint(1, 50),
                volume=volume + random.randint(-500, 500),
                keyword_type=ktype,
            ))

        return keywords
