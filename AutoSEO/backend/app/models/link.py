"""
Модели Модулей 2 и 3 — Бесплатные и платные ссылки.
DonorPlatform, FreeLink, KeywordCluster, PaidLink, UsedDonor.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DonorPlatform(Base):
    """Площадка-донор для бесплатного линкбилдинга."""
    __tablename__ = "donor_platforms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    platform_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="directory | forum | profile | article"
    )
    requires_logo: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_captcha: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", comment="active | spam | closed | blocked"
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    free_links = relationship("FreeLink", back_populates="donor", lazy="selectin")


class FreeLink(Base):
    """Размещённая бесплатная ссылка с мониторингом живучести и индексации."""
    __tablename__ = "free_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("donor_platforms.id"), nullable=False
    )
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    placed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anchor_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promo_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="pending",
        comment="pending | placed | verified | dead | reindexing"
    )
    last_http_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="free_links")
    donor = relationship("DonorPlatform", back_populates="free_links")


class KeywordCluster(Base):
    """Кластер ключевых слов для платного линкбилдинга."""
    __tablename__ = "keyword_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    main_keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    landing_page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # LSI-ключи, варианты анкоров, структура ТОПа
    lsi_keywords: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    anchor_variants: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    serp_structure: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="keyword_clusters")
    paid_links = relationship("PaidLink", back_populates="cluster", lazy="selectin")


class PaidLink(Base):
    """Платная ссылка (аутрич/биржа) с полным контролем генерации и публикации."""
    __tablename__ = "paid_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("keyword_clusters.id"), nullable=True
    )

    donor_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    donor_page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    article_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    article_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_images: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    meta_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="draft",
        comment="draft | review | submitted | published | indexed | rejected"
    )
    tone_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    structure_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    miralinks_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_indexed_google: Mapped[bool] = mapped_column(Boolean, default=False)
    is_indexed_yandex: Mapped[bool] = mapped_column(Boolean, default=False)

    # Инструкции для вебмастера (автогенерация)
    webmaster_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_index_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="paid_links")
    cluster = relationship("KeywordCluster", back_populates="paid_links")


class UsedDonor(Base):
    """Анти-дубль система: БД использованных доноров для конкретного проекта."""
    __tablename__ = "used_donors"
    __table_args__ = (
        UniqueConstraint("project_id", "donor_domain", name="uq_project_donor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    donor_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    paid_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paid_links.id"), nullable=True
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="used_donors")
