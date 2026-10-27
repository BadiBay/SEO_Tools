"""
Semrush SEO Metrics Provider.
Используется для: Domain Rating, backlinks, динамика ссылочной массы.
API Docs: https://developer.semrush.com/api/
"""
import httpx
from app.integrations.base import (
    BaseSEOMetricsProvider, DomainMetrics,
    VisibilityPoint, PageMetrics, KeywordInfo,
)
from app.config import settings


class SemrushProvider(BaseSEOMetricsProvider):
    """Провайдер метрик Semrush API."""

    BASE_URL = "https://api.semrush.com"

    def __init__(self, api_key: str | None = None):
        from app.utils.key_manager import KeyManager
        self.api_key = api_key or KeyManager.get_active_key("semrush")
        if not self.api_key:
            raise ValueError("No active API key found for Semrush")

    async def _request(self, params: dict) -> str:
        """Semrush API возвращает CSV/TSV, не JSON."""
        params["key"] = self.api_key
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            return resp.text

    def _parse_tsv(self, text: str) -> list[dict]:
        """Парсинг TSV-ответа Semrush в список словарей."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return []
        headers = lines[0].split(";")
        result = []
        for line in lines[1:]:
            values = line.split(";")
            result.append(dict(zip(headers, values)))
        return result

    async def get_domain_metrics(self, domain: str) -> DomainMetrics:
        # Domain overview
        text = await self._request({
            "type": "domain_ranks",
            "domain": domain,
            "database": "ru",
            "export_columns": "Dn,Rk,Or,Ot,Oc,Ad,At,Ac",
        })
        rows = self._parse_tsv(text)
        info = rows[0] if rows else {}

        # Backlinks overview
        bl_text = await self._request({
            "type": "backlinks_overview",
            "target": domain,
            "target_type": "root_domain",
            "export_columns": "ascore,total,domains_num",
        })
        bl_rows = self._parse_tsv(bl_text)
        bl_info = bl_rows[0] if bl_rows else {}

        return DomainMetrics(
            domain=domain,
            traffic=float(info.get("Ot", 0)),
            visibility=int(info.get("Or", 0)),
            domain_rating=float(bl_info.get("ascore", 0)),
            backlinks_count=int(bl_info.get("total", 0)),
            referring_domains=int(bl_info.get("domains_num", 0)),
            has_ppc=int(info.get("Ad", 0)) > 0,
            ppc_budget=float(info.get("Ac", 0)) if info.get("Ac") else None,
            raw={"domain_ranks": info, "backlinks": bl_info},
        )

    async def get_visibility_history(self, domain: str, months: int = 12) -> list[VisibilityPoint]:
        text = await self._request({
            "type": "domain_rank_history",
            "domain": domain,
            "database": "ru",
            "export_columns": "Dt,Rk,Or,Ot",
            "display_limit": months,
        })
        return [
            VisibilityPoint(date=r.get("Dt", ""), visibility=float(r.get("Or", 0)))
            for r in self._parse_tsv(text)
        ]

    async def get_top_pages(self, domain: str, limit: int = 20) -> list[PageMetrics]:
        text = await self._request({
            "type": "domain_organic",
            "domain": domain,
            "database": "ru",
            "export_columns": "Ph,Po,Nq,Ur",
            "display_limit": limit,
            "display_sort": "tr_desc",
        })
        rows = self._parse_tsv(text)

        # Группируем по URL
        pages_map: dict[str, PageMetrics] = {}
        for r in rows:
            url = r.get("Ur", "")
            if url not in pages_map:
                pages_map[url] = PageMetrics(url=url)
            pages_map[url].keywords_count += 1

        return list(pages_map.values())[:limit]

    async def get_keywords(self, domain: str, limit: int = 100) -> list[KeywordInfo]:
        text = await self._request({
            "type": "domain_organic",
            "domain": domain,
            "database": "ru",
            "export_columns": "Ph,Po,Nq",
            "display_limit": limit,
        })
        return [
            KeywordInfo(
                keyword=r.get("Ph", ""),
                position=int(r.get("Po", 0)),
                volume=int(r.get("Nq", 0)),
            )
            for r in self._parse_tsv(text)
        ]
