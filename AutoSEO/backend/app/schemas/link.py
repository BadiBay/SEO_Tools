"""
Pydantic schemas для Модулей 2 и 3 — Бесплатные и платные ссылки.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional


# === Keyword Cluster ===

class KeywordClusterCreate(BaseModel):
    project_id: UUID
    main_keyword: str
    landing_page_url: Optional[str] = None


class KeywordClusterResponse(BaseModel):
    id: UUID
    project_id: UUID
    main_keyword: str
    landing_page_url: Optional[str]
    lsi_keywords: Optional[dict]
    anchor_variants: Optional[dict]
    serp_structure: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# === Paid Link ===

class PaidLinkCreate(BaseModel):
    """Создание заявки на платную ссылку."""
    project_id: UUID
    main_keyword: str
    landing_page_url: Optional[str] = None
    donor_domain: str
    donor_page_url: Optional[str] = None


class PaidLinkResponse(BaseModel):
    id: UUID
    project_id: UUID
    cluster_id: Optional[UUID]

    donor_domain: str
    donor_page_url: Optional[str]

    article_title: Optional[str]
    article_html: Optional[str]
    article_images: Optional[dict]
    
    meta_title: Optional[str]
    meta_description: Optional[str]

    status: str
    tone_check_passed: Optional[bool]
    structure_check_passed: Optional[bool]
    
    miralinks_order_id: Optional[str]
    price: Optional[float]
    
    is_indexed_google: bool
    is_indexed_yandex: bool
    
    webmaster_instructions: Optional[str]
    
    published_at: Optional[datetime]
    last_index_check_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaidLinkListResponse(BaseModel):
    items: list[PaidLinkResponse]
    total: int


class PaidLinkImportItem(BaseModel):
    domain: str
    placed_url: Optional[str] = None
    price: Optional[float] = None
    miralinks_order_id: Optional[str] = None


class PaidLinkImportRequest(BaseModel):
    links: list[PaidLinkImportItem]
