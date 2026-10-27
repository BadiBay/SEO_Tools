"""
Базовые абстрактные классы для всех адаптеров интеграции.
Единый интерфейс, позволяющий переключать провайдеров без изменения бизнес-логики.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ========================
# LLM Provider
# ========================

@dataclass
class LLMResponse:
    """Стандартный ответ от LLM-провайдера."""
    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    raw: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Абстрактный LLM-провайдер. Текст, Vision, генерация изображений."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Генерация текста по промпту."""
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        **kwargs,
    ) -> LLMResponse:
        """Анализ изображения (Vision)."""
        ...

    async def generate_image(
        self,
        prompt: str,
        **kwargs,
    ) -> bytes:
        """Генерация изображения (опционально)."""
        raise NotImplementedError("Image generation not supported by this provider")

    async def search_and_analyze(
        self,
        query: str,
        system_prompt: str = "",
        **kwargs,
    ) -> LLMResponse:
        """Поиск + анализ (для Perplexity). Fallback — обычная генерация."""
        return await self.generate_text(query, system_prompt, **kwargs)


# ========================
# SEO Metrics Provider
# ========================

@dataclass
class DomainMetrics:
    """Стандартные SEO-метрики домена."""
    domain: str
    traffic: Optional[float] = None
    visibility: Optional[int] = None
    top10_count: Optional[int] = None
    top50_count: Optional[int] = None
    domain_rating: Optional[float] = None
    backlinks_count: Optional[int] = None
    referring_domains: Optional[int] = None
    has_ppc: Optional[bool] = None
    ppc_budget: Optional[float] = None
    ppc_budget_trend: Optional[str] = None
    link_trend: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class VisibilityPoint:
    """Точка на графике видимости."""
    date: str
    visibility: float


@dataclass
class PageMetrics:
    """Метрики страницы."""
    url: str
    traffic: float = 0
    traffic_share: float = 0
    keywords_count: int = 0
    page_type: str = ""  # commercial | info | main | category


@dataclass
class KeywordInfo:
    """Информация о ключевом слове."""
    keyword: str
    position: int = 0
    volume: int = 0
    keyword_type: str = ""  # brand | commercial | info | navigational


class BaseSEOMetricsProvider(ABC):
    """Абстрактный провайдер SEO-метрик."""

    @abstractmethod
    async def get_domain_metrics(self, domain: str) -> DomainMetrics:
        ...

    @abstractmethod
    async def get_visibility_history(self, domain: str, months: int = 12) -> list[VisibilityPoint]:
        ...

    @abstractmethod
    async def get_top_pages(self, domain: str, limit: int = 20) -> list[PageMetrics]:
        ...

    @abstractmethod
    async def get_keywords(self, domain: str, limit: int = 100) -> list[KeywordInfo]:
        ...


# ========================
# SERP Parser
# ========================

@dataclass
class SERPResult:
    """Один результат выдачи."""
    position: int
    domain: str
    url: str
    title: str
    snippet: str = ""


class BaseSERPParser(ABC):
    """Абстрактный парсер поисковой выдачи."""

    @abstractmethod
    async def parse_serp(
        self,
        query: str,
        search_engine: str = "google",
        region: str = "ru",
        top_n: int = 10,
    ) -> list[SERPResult]:
        ...


# ========================
# Notification Sender
# ========================

class BaseNotificationSender(ABC):
    """Абстрактный отправитель уведомлений."""

    @abstractmethod
    async def send(
        self,
        title: str,
        message: str,
        severity: str = "info",
        **kwargs,
    ) -> bool:
        ...
