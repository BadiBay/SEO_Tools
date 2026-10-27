"""
Пакет интеграций — адаптеры внешних сервисов.
"""
from app.integrations.base import (
    BaseLLMProvider,
    BaseSEOMetricsProvider,
    BaseSERPParser,
    BaseNotificationSender,
    LLMResponse,
    DomainMetrics,
    SERPResult,
)

__all__ = [
    "BaseLLMProvider",
    "BaseSEOMetricsProvider",
    "BaseSERPParser",
    "BaseNotificationSender",
    "LLMResponse",
    "DomainMetrics",
    "SERPResult",
]
