"""
Модели Модуля 1 — Анализ конкурентов.
CompetitorReport, MarkerQuery, Competitor.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompetitorReport(Base):
    """Отчёт по анализу конкурентов — привязан к одному запуску пайплайна."""
    __tablename__ = "competitor_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False, unique=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    run = relationship("PipelineRun", back_populates="competitor_report")
    project = relationship("Project", back_populates="competitor_reports")
    marker_queries = relationship("MarkerQuery", back_populates="report", lazy="selectin")
    competitors = relationship("Competitor", back_populates="report", lazy="selectin")


class MarkerQuery(Base):
    """Маркерный запрос для поиска конкурентов в выдаче."""
    __tablename__ = "marker_queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitor_reports.id"), nullable=False
    )
    query_text: Mapped[str] = mapped_column(String(500), nullable=False)
    priority_direction: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Маржинальное направление бизнеса"
    )
    search_engine: Mapped[str] = mapped_column(
        String(20), default="google", comment="yandex | google"
    )

    # Relationships
    report = relationship("CompetitorReport", back_populates="marker_queries")


class Competitor(Base):
    """Найденный конкурент с полным набором метрик и анализа."""
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitor_reports.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    # === AI-классификация ===
    is_direct_competitor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_classification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Метрики Keys.so ===
    traffic_keys_so: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility_keys_so: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top10_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top50_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # === Тренд видимости (Vision AI) ===
    visibility_trend: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="growth | decline | stagnation"
    )
    visibility_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="green | yellow | red"
    )
    visibility_screenshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # === PPC (контекстная реклама) ===
    has_ppc: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ppc_budget_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    ppc_budget_trend: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="growing | stable | declining"
    )

    # === Семантика — флаги ===
    has_brand_queries: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_commercial_queries: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_info_queries: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # === Возраст домена ===
    domain_age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # === Semrush — авторитетность ===
    semrush_domain_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    semrush_backlinks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semrush_link_trend: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="growing | stable | declining"
    )

    # === JSONB-поля для сложных структур ===
    # Страницы-лидеры: [{"url": "/catalog", "type": "commercial", "traffic_share": 45}, ...]
    top_pages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # УТП и структура (Perplexity): {"utps": [...], "categories": [...], "main_focus": "..."}
    utp_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Структура семантики: {"brand": 15, "commercial": 60, "info": 25, "total_queries": 1200}
    semantic_structure: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Полный дамп сырых метрик от провайдеров
    raw_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    report = relationship("CompetitorReport", back_populates="competitors")

    def __repr__(self) -> str:
        status = "✓" if self.is_direct_competitor else "✗"
        return f"<Competitor {self.domain} [{status}]>"
