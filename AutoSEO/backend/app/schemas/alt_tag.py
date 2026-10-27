from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


# --- ImageAlt ---
class ImageAltBase(BaseModel):
    image_src: str
    page_url: Optional[str] = None
    original_alt: Optional[str] = None


class ImageAltImport(ImageAltBase):
    pass


class ImageAltResponse(ImageAltBase):
    id: UUID
    batch_id: UUID
    page_h1: Optional[str] = None
    page_title: Optional[str] = None
    original_alt_is_junk: bool
    generated_alt: Optional[str] = None
    generated_title: Optional[str] = None
    image_type: str
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# --- AltTagBatch ---
class AltTagBatchImportRequest(BaseModel):
    images: List[ImageAltImport]


class AltTagBatchResponse(BaseModel):
    id: UUID
    run_id: UUID
    project_id: UUID
    site_description: Optional[str] = None
    total_images: int
    processed_images: int
    skipped_svg: int
    created_at: datetime
    images: Optional[List[ImageAltResponse]] = None

    class Config:
        from_attributes = True


class AltTagBatchListResponse(BaseModel):
    items: List[AltTagBatchResponse]
    total: int
