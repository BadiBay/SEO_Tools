"""
Модели PipelineRun и PipelineStepLog — отслеживание запусков пайплайнов
и их шагов с человекочитаемыми статусами и логами.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ModuleType(str, enum.Enum):
    COMPETITORS = "competitors"
    FREE_LINKS = "free_links"
    PAID_LINKS = "paid_links"
    ALT_TAGS = "alt_tags"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineRun(Base):
    """Запуск пайплайна одного из 4 модулей."""
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    module_type: Mapped[ModuleType] = mapped_column(
        SAEnum(ModuleType, name="module_type_enum"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status_enum"), default=RunStatus.PENDING
    )

    # Конфигурация запуска (регион, глубина ТОПа, настройки)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Прогресс: {"current_step": 3, "total_steps": 14, "percent": 21, "message": "Парсинг ТОП-10..."}
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="pipeline_runs")
    step_logs = relationship("PipelineStepLog", back_populates="run", lazy="selectin", order_by="PipelineStepLog.step_number")
    competitor_report = relationship("CompetitorReport", back_populates="run", uselist=False)
    alt_tag_batch = relationship("AltTagBatch", back_populates="run", uselist=False)

    def __repr__(self) -> str:
        return f"<PipelineRun {self.module_type.value} [{self.status.value}]>"


class PipelineStepLog(Base):
    """Лог каждого шага пайплайна."""
    __tablename__ = "pipeline_step_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Данные шага (входные/выходные)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run = relationship("PipelineRun", back_populates="step_logs")

    def __repr__(self) -> str:
        return f"<StepLog #{self.step_number} '{self.step_name}' [{self.status}]>"
