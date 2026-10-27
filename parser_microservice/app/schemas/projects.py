from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

class ProjectBase(BaseModel):
    name: str = Field(..., description="Имя проекта (например, 'Сеть стоматологий')")
    links: List[str] = Field(default_factory=list, description="Список URL для парсинга")
    company: Optional[str] = Field(None, description="Название компании")
    direction: Optional[str] = Field(None, description="Направление бизнеса")
    city: Optional[str] = Field(None, description="Город")
    address: Optional[str] = Field(None, description="Дополнительный адрес")
    website: Optional[str] = Field(None, description="Вебсайт")

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    links: Optional[List[str]] = None
    company: Optional[str] = None
    direction: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None

class ProjectModel(ProjectBase):
    id: str = Field(..., description="Уникальный идентификатор проекта")
    created_at: str = Field(..., description="Дата создания проекта (ISO)")

class ScanResultItem(BaseModel):
    url: str
    status: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    new_reviews: List[dict] = Field(default_factory=list)
    error_message: Optional[str] = None

class ProjectScanResponse(BaseModel):
    project_id: str
    scan_date: str
    results: List[ScanResultItem]
