"""
Модель SystemSetting — Глобальные настройки системы (Key-Value хранилище).
"""
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True, comment="Например: api_keys, user_profile, billing")
    value: Mapped[dict | list | str | int | bool | None] = mapped_column(JSONB, nullable=True)
