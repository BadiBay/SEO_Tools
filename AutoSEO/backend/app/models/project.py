"""
Модель Project — центральная сущность, к которой привязаны все модули.
Один клиент/домен = один проект.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)

    # Приоритеты клиента (маржинальные направления, ключевые услуги/категории)
    client_priorities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Медиа-ассеты клиента (логотип, favicon — парсятся при создании проекта)
    client_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Описание тематики сайта (1 предложение, генерируется LLM)
    site_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships (lazy='select' by default — load on access, not upfront)
    pipeline_runs = relationship("PipelineRun", back_populates="project")
    competitor_reports = relationship("CompetitorReport", back_populates="project")
    free_links = relationship("FreeLink", back_populates="project")
    paid_links = relationship("PaidLink", back_populates="project")
    keyword_clusters = relationship("KeywordCluster", back_populates="project")
    used_donors = relationship("UsedDonor", back_populates="project")
    alt_tag_batches = relationship("AltTagBatch", back_populates="project")
    notifications = relationship("Notification", back_populates="project")

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.domain})>"
