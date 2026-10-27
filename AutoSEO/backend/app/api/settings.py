"""
API — Настройки (Settings).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.system_setting import SystemSetting
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingItem(BaseModel):
    key: str
    value: Any


class SettingsUpdateRequest(BaseModel):
    settings: list[SettingItem]


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Получить все системные настройки."""
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


@router.put("")
async def update_settings(data: SettingsUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Массовое обновление настроек."""
    from app.config import settings as global_settings
    
    for item in data.settings:
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == item.key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = item.value
        else:
            setting = SystemSetting(key=item.key, value=item.value)
            db.add(setting)
            
        # Update in-memory settings if applicable
        if hasattr(global_settings, item.key):
            setattr(global_settings, item.key, item.value)
            
    await db.commit()
    return {"status": "ok"}
