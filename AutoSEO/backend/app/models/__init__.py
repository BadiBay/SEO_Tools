"""Пакет моделей SQLAlchemy."""
from app.models.project import Project
from app.models.pipeline import PipelineRun, RunStatus, ModuleType
from app.models.competitor import Competitor, CompetitorReport
from app.models.notification import Notification
from app.models.link import PaidLink, FreeLink, DonorPlatform
from app.models.alt_tag import AltTagBatch, ImageAlt
from app.models.system_setting import SystemSetting

__all__ = [
    "Project",
    "PipelineRun",
    "RunStatus",
    "ModuleType",
    "Competitor",
    "CompetitorReport",
    "Notification",
    "PaidLink",
    "FreeLink",
    "DonorPlatform",
    "AltTagBatch",
    "ImageAlt",
    "SystemSetting",
]
