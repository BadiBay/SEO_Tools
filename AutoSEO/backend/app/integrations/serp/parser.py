"""
SERP Parser — парсер поисковой выдачи.
Содержит кастомный парсер и mock для разработки.
В будущем — подключение SerpAPI/Serper.dev.
"""
import random
from urllib.parse import urlparse
from app.integrations.base import BaseSERPParser, SERPResult


class MockSERPParser(BaseSERPParser):
    """Заглушка SERP-парсера с реалистичными доменами."""

    MOCK_DOMAINS = {
        "google": [
            "okna-moskva.ru", "plastikovye-okna.com", "rehau-okna.ru",
            "oknafabrika.ru", "okna-st.ru", "dveri-okna.com",
            "brusbox.ru", "veka-okna.ru", "kaleva.ru", "oknarik.ru",
            "ozon.ru", "wildberries.ru", "avito.ru",  # маркетплейсы для фильтрации
            "yandex.ru", "dzen.ru",  # агрегаторы
        ],
        "yandex": [
            "okna-moskva.ru", "rehau-okna.ru", "oknafabrika.ru",
            "plastikovye-okna.com", "okna-st.ru", "kaleva.ru",
            "brusbox.ru", "dveri-okna.com", "oknarik.ru", "veka-okna.ru",
            "market.yandex.ru", "ozon.ru",  # маркетплейсы
        ],
    }

    async def parse_serp(
        self,
        query: str,
        search_engine: str = "google",
        region: str = "ru",
        top_n: int = 10,
    ) -> list[SERPResult]:
        seed = hash(query) % 10000
        random.seed(seed)

        domains = self.MOCK_DOMAINS.get(search_engine, self.MOCK_DOMAINS["google"])
        selected = random.sample(domains, min(top_n, len(domains)))

        results = []
        for i, domain in enumerate(selected, 1):
            results.append(SERPResult(
                position=i,
                domain=domain,
                url=f"https://{domain}/",
                title=f"[Mock] {query} — {domain}",
                snippet=f"Результат поиска по запросу «{query}» на сайте {domain}",
            ))

        return results
