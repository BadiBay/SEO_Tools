"""
Pydantic schemas для проектов и пайплайнов.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional


# === Project ===

class ProjectCreate(BaseModel):
    """Создание нового проекта."""
    name: str = Field(..., min_length=1, max_length=255, description="Название проекта")
    domain: str = Field(..., min_length=3, max_length=255, description="Домен сайта (без https://)")
    region: Optional[str] = Field(None, max_length=100, description="Целевой регион")
    client_priorities: Optional[dict] = Field(
        None,
        description="Приоритеты клиента: {'directions': ['окна ПВХ', 'двери'], 'top_services': [...], 'notes': '...'}"
    )


class ProjectUpdate(BaseModel):
    """Обновление проекта."""
    name: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    client_priorities: Optional[dict] = None
    is_active: Optional[bool] = None

class ProjectFreeLinksInfoUpdate(BaseModel):
    """Обновление данных для бесплатных ссылок (сохраняется в client_priorities)."""
    target_url: Optional[str] = None
    promo_text: Optional[str] = None
    account_data: Optional[str] = None


class ProjectResponse(BaseModel):
    """Ответ с данными проекта."""
    id: UUID
    name: str
    domain: str
    region: Optional[str]
    client_priorities: Optional[dict]
    client_logo_url: Optional[str]
    favicon_url: Optional[str]
    site_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Список проектов."""
    items: list[ProjectResponse]
    total: int


# === Pipeline Run ===

class PipelineRunResponse(BaseModel):
    """Ответ со статусом запуска пайплайна."""
    id: UUID
    project_id: UUID
    module_type: str
    status: str
    config: Optional[dict]
    progress: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineStepLogResponse(BaseModel):
    """Лог шага пайплайна."""
    id: UUID
    step_number: int
    step_name: str
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class PipelineRunDetailResponse(PipelineRunResponse):
    """Детальный ответ со всеми логами шагов."""
    steps: list[PipelineStepLogResponse] = []
