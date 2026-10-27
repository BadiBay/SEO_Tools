from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# --- DonorPlatform ---
class DonorPlatformResponse(BaseModel):
    id: UUID
    name: str
    url: str
    platform_type: str
    requires_logo: bool
    requires_captcha: bool
    status: str
    last_checked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DonorPlatformCreate(BaseModel):
    name: str
    url: str
    platform_type: str = "other"
    requires_logo: bool = False
    requires_captcha: bool = False


class DonorPlatformListResponse(BaseModel):
    items: list[DonorPlatformResponse]
    total: int


# --- FreeLink ---
class FreeLinkCreate(BaseModel):
    project_id: UUID
    donor_id: UUID
    target_url: str


class FreeLinkResponse(BaseModel):
    id: UUID
    project_id: UUID
    donor_id: UUID
    target_url: str
    placed_url: Optional[str] = None
    anchor_text: Optional[str] = None
    email_alias: Optional[str] = None
    promo_text: Optional[str] = None
    status: str
    last_http_code: Optional[int] = None
    is_indexed: bool
    placed_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    created_at: datetime
    
    # Чтобы во фронтенде сразу выводить название и URL донора
    donor: Optional[DonorPlatformResponse] = None

    class Config:
        from_attributes = True


class FreeLinkListResponse(BaseModel):
    items: list[FreeLinkResponse]
    total: int


class FreeLinkVerifyRequest(BaseModel):
    placed_url: str


class FreeLinkImportItem(BaseModel):
    name: str
    url: str
    platform_type: str = "other"
    placed_url: Optional[str] = None


class FreeLinkImportRequest(BaseModel):
    donors: list[FreeLinkImportItem]
