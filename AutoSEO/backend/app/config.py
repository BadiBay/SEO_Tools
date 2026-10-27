"""
AutoSEO Platform — Configuration
Единый файл конфигурации через pydantic-settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Все настройки приложения из переменных окружения."""

    # === App ===
    app_secret_key: str = "change-me-to-random-string"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # === Database ===
    database_url: str = "postgresql+asyncpg://autoseo:autoseo_secret_change_me@localhost:5432/autoseo"

    # === Redis ===
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # === MinIO ===
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "autoseo_minio"
    minio_root_password: str = "minio_secret_change_me"
    minio_bucket: str = "autoseo-media"
    minio_use_ssl: bool = False

    # === LLM Providers ===
    default_llm_provider: str = "mock"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None

    # === SEO APIs ===
    keys_so_api_key: Optional[str] = None
    semrush_api_key: Optional[str] = None

    # === Google APIs ===
    google_sheets_credentials_json: Optional[str] = None
    google_indexing_credentials_json: Optional[str] = None

    # === SERP ===
    serp_provider: str = "custom"
    serpapi_key: Optional[str] = None
    serper_api_key: Optional[str] = None

    # === Notifications ===
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_email_from: str = "noreply@autoseo.local"

    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    webhook_url: Optional[str] = None

    # === Rate Limiting ===
    default_rate_limit_delay: float = 0.7  # секунд между запросами к API
    llm_batch_size: int = 5  # размер батча для LLM-запросов
    serp_batch_size: int = 10  # размер батча для SERP-парсинга

    # === Advanced Settings (Dicts for multi-key and models) ===
    gemini_settings: Optional[dict] = None
    openai_settings: Optional[dict] = None
    anthropic_settings: Optional[dict] = None
    perplexity_settings: Optional[dict] = None
    keys_so_settings: Optional[dict] = None
    semrush_settings: Optional[dict] = None
    serper_settings: Optional[dict] = None
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}


settings = Settings()
