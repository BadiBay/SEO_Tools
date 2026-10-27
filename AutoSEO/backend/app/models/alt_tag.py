"""
Модели Модуля 4 — Генерация Alt-тегов.
AltTagBatch, ImageAlt.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AltTagBatch(Base):
    """Батч обработки изображений для генерации alt-тегов."""
    __tablename__ = "alt_tag_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False, unique=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    site_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_images: Mapped[int] = mapped_column(Integer, default=0)
    processed_images: Mapped[int] = mapped_column(Integer, default=0)
    skipped_svg: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    run = relationship("PipelineRun", back_populates="alt_tag_batch")
    project = relationship("Project", back_populates="alt_tag_batches")
    images = relationship("ImageAlt", back_populates="batch", lazy="selectin")


class ImageAlt(Base):
    """Одно изображение с оригинальным и сгенерированным alt-тегом."""
    __tablename__ = "image_alts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alt_tag_batches.id"), nullable=False
    )

    image_src: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    page_h1: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    original_alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_alt_is_junk: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="True если alt — техническое имя файла (IMG_4048, frame_2 и т.п.)"
    )
    generated_alt: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    image_type: Mapped[str] = mapped_column(
        String(20), default="raster", comment="raster | vector | icon"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending",
        comment="pending | processing | done | skipped | error"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    batch = relationship("AltTagBatch", back_populates="images")
