"""
Keys.so SEO Metrics Provider.
Документация: https://keys.so/api/
"""
import httpx
from app.integrations.base import (
    BaseSEOMetricsProvider, DomainMetrics,
    VisibilityPoint, PageMetrics, KeywordInfo,
)
from app.config import settings


class KeysSoProvider(BaseSEOMetricsProvider):
    """Провайдер метрик Keys.so."""

    BASE_URL = "https://api.keys.so/v2"

    def __init__(self, api_key: str | None = None):
        from app.utils.key_manager import KeyManager
        self.api_key = api_key or KeyManager.get_active_key("keys_so")
        if not self.api_key:
            raise ValueError("No active API key found for Keys.so")

    async def _request(self, endpoint: str, params: dict) -> dict:
        params["token"] = self.api_key
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_domain_metrics(self, domain: str) -> DomainMetrics:
        data = await self._request("summary", {"domain": domain, "se": "google", "region": "ru"})
        info = data.get("result", {})
        return DomainMetrics(
            domain=domain,
            traffic=info.get("traffic"),
            visibility=info.get("visibility"),
            top10_count=info.get("top10"),
            top50_count=info.get("top50"),
            has_ppc=info.get("ads_count", 0) > 0,
            ppc_budget=info.get("ads_budget"),
            raw=data,
        )

    async def get_visibility_history(self, domain: str, months: int = 12) -> list[VisibilityPoint]:
        data = await self._request("domain/history", {"domain": domain, "se": "google", "region": "ru"})
        points = []
        for item in data.get("result", [])[-months:]:
            points.append(VisibilityPoint(date=item.get("date", ""), visibility=item.get("visibility", 0)))
        return points

    async def get_top_pages(self, domain: str, limit: int = 20) -> list[PageMetrics]:
        data = await self._request("domain/pages", {"domain": domain, "se": "google", "region": "ru", "limit": limit})
        return [
            PageMetrics(
                url=p.get("page", ""),
                traffic=p.get("traffic", 0),
                keywords_count=p.get("keywords", 0),
            )
            for p in data.get("result", [])
        ]

    async def get_keywords(self, domain: str, limit: int = 100) -> list[KeywordInfo]:
        data = await self._request("domain/keywords", {"domain": domain, "se": "google", "region": "ru", "limit": limit})
        return [
            KeywordInfo(
                keyword=k.get("keyword", ""),
                position=k.get("position", 0),
                volume=k.get("volume", 0),
            )
            for k in data.get("result", [])
        ]
