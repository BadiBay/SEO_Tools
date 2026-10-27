import logging
from sqlalchemy import select
from app.config import settings
from app.database import async_session_factory
from app.models.system_setting import SystemSetting
from app.models.notification import Notification

logger = logging.getLogger(__name__)

class KeyManager:
    """Утилита для управления списками API-ключей и их статусами."""

    @staticmethod
    async def get_service_config(service_name: str) -> dict:
        """
        Возвращает конфигурацию сервиса из БД (если есть), иначе из .env
        """
        setting_key = f"{service_name}_settings"
        
        # Читаем из БД каждый раз, чтобы всегда иметь актуальные ключи (Celery worker long-lived)
        async with async_session_factory() as db:
            result = await db.execute(select(SystemSetting).where(SystemSetting.key == setting_key))
            db_setting = result.scalar_one_or_none()
            if db_setting and isinstance(db_setting.value, dict):
                return db_setting.value
            
        # Fallback к старым переменным окружения
        env_key = f"{service_name}_api_key"
        legacy_key = getattr(settings, env_key, None)
        
        default_model = ""
        if service_name == "gemini":
            default_model = "gemini-2.5-flash"
        elif service_name == "openai":
            default_model = "gpt-4o"
        elif service_name == "anthropic":
            default_model = "claude-3-5-sonnet-20240620"
        elif service_name == "perplexity":
            default_model = "sonar-pro"
            
        if legacy_key:
            return {"model": default_model, "keys": [{"value": legacy_key, "status": "active"}]}
            
        return {"model": default_model, "keys": []}

    @staticmethod
    async def get_active_key(service_name: str) -> str | None:
        """Получить первый активный ключ для сервиса."""
        config = await KeyManager.get_service_config(service_name)
        for key_obj in config.get("keys", []):
            if key_obj.get("status") == "active":
                return key_obj.get("value")
        return None
        
    @staticmethod
    async def get_model(service_name: str) -> str:
        """Получить выбранную модель для сервиса."""
        config = await KeyManager.get_service_config(service_name)
        return config.get("model", "")

    @staticmethod
    async def mark_key_exhausted(service_name: str, key_value: str):
        """
        Помечает ключ как 'exhausted' (исчерпан) и сохраняет в БД.
        Создает системное уведомление.
        """
        config = await KeyManager.get_service_config(service_name)
        updated = False
        
        for key_obj in config.get("keys", []):
            if key_obj.get("value") == key_value and key_obj.get("status") == "active":
                key_obj["status"] = "exhausted"
                updated = True
                
        if updated:
            setting_key = f"{service_name}_settings"
            
            # Обновляем в памяти (чтобы сразу подхватилось)
            setattr(settings, setting_key, config)
            
            # Сохраняем в БД
            async with async_session_factory() as db:
                result = await db.execute(select(SystemSetting).where(SystemSetting.key == setting_key))
                setting = result.scalar_one_or_none()
                if setting:
                    setting.value = config
                else:
                    setting = SystemSetting(key=setting_key, value=config)
                    db.add(setting)
                    
                # Создаем уведомление
                masked_key = f"...{key_value[-4:]}" if len(key_value) > 4 else "***"
                notif = Notification(
                    channel="internal",
                    event_type="api_key_exhausted",
                    severity="warning",
                    title=f"Ключ API исчерпан ({service_name.upper()})",
                    message=f"Ключ {masked_key} получил ошибку 429 (Quota Exceeded) и был автоматически отключен. Система перейдет к следующему активному ключу (если он есть)."
                )
                db.add(notif)
                
                await db.commit()
            
            logger.warning(f"Key for {service_name} marked as exhausted: {masked_key}")
