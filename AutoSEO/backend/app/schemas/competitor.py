"""
Pydantic schemas для Модуля 1 — Анализ конкурентов.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional


class CompetitorAnalysisRequest(BaseModel):
    """Запрос на запуск анализа конкурентов."""
    project_id: UUID
    config: Optional[dict] = Field(
        default_factory=lambda: {
            "search_engines": ["google", "yandex"],
            "top_depth": 10,
            "max_competitors": 15,
            "region": "ru",
        },
        description="Настройки анализа"
    )


class ClientPrioritiesRequest(BaseModel):
    """Форма приоритетов клиента."""
    project_id: UUID
    directions: list[str] = Field(
        ..., min_length=1,
        description="Маржинальные направления бизнеса (например: ['окна ПВХ', 'балконы', 'двери'])"
    )
    top_services: Optional[list[str]] = Field(
        None,
        description="Ключевые услуги/товары"
    )
    target_audience: Optional[str] = Field(
        None,
        description="Целевая аудитория"
    )
    notes: Optional[str] = Field(
        None,
        description="Дополнительные заметки"
    )


class CompetitorResponse(BaseModel):
    """Ответ с данными конкурента."""
    id: UUID
    domain: str
    is_direct_competitor: Optional[bool]
    ai_classification_reason: Optional[str]

    # Метрики
    traffic_keys_so: Optional[float]
    visibility_keys_so: Optional[int]
    top10_count: Optional[int]
    top50_count: Optional[int]

    # Тренды
    visibility_trend: Optional[str]
    visibility_color: Optional[str]
    visibility_screenshot_url: Optional[str]

    # PPC
    has_ppc: Optional[bool]
    ppc_budget_estimate: Optional[float]
    ppc_budget_trend: Optional[str]

    # Семантика
    has_brand_queries: Optional[bool]
    has_commercial_queries: Optional[bool]
    has_info_queries: Optional[bool]

    # Возраст
    domain_age_years: Optional[int]

    # Semrush
    semrush_domain_rating: Optional[float]
    semrush_backlinks_count: Optional[int]
    semrush_link_trend: Optional[str]

    # Сложные структуры
    top_pages: Optional[list]
    utp_analysis: Optional[dict]
    semantic_structure: Optional[dict]

    model_config = {"from_attributes": True}


class CompetitorReportResponse(BaseModel):
    """Полный отчёт по конкурентам."""
    id: UUID
    run_id: UUID
    project_id: UUID
    created_at: datetime
    competitors: list[CompetitorResponse] = []
    marker_queries_count: int = 0
    direct_competitors_count: int = 0
    total_competitors: int = 0

    model_config = {"from_attributes": True}
