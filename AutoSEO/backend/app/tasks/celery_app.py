"""
Celery Application — конфигурация и запуск.
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "autoseo",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.competitor_tasks",
        "app.tasks.link_tasks",
        "app.tasks.free_link_tasks",
        "app.tasks.alt_tag_tasks",
        "app.tasks.scheduled_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Очереди по модулям
    task_routes={
        "app.tasks.competitor_tasks.*": {"queue": "competitors"},
        "app.tasks.link_tasks.*": {"queue": "links"},
        "app.tasks.free_link_tasks.*": {"queue": "links"},
        "app.tasks.alt_tag_tasks.*": {"queue": "alt_tags"},
        "app.tasks.scheduled_tasks.*": {"queue": "default"},
    },

    # Расписание регулярных задач (Celery Beat)
    beat_schedule={
        # Проверка живучести бесплатных ссылок — раз в месяц (1-е число)
        "check-free-links-alive": {
            "task": "app.tasks.scheduled_tasks.check_free_links_alive",
            "schedule": crontab(day_of_month="1", hour="3", minute="0"),
            "args": (),
        },
        # Аудит базы доноров — раз в месяц (15-е число)
        "audit-donor-platforms": {
            "task": "app.tasks.scheduled_tasks.audit_donor_platforms",
            "schedule": crontab(day_of_month="15", hour="4", minute="0"),
            "args": (),
        },
        # Проверка индексации платных ссылок — каждые 2 недели (1-й и 15-й)
        "check-paid-links-indexation": {
            "task": "app.tasks.scheduled_tasks.check_paid_links_indexation",
            "schedule": crontab(day_of_month="1,15", hour="5", minute="0"),
            "args": (),
        },
        # Проверка индексации бесплатных ссылок — каждые 2 недели
        "check-free-links-indexation": {
            "task": "app.tasks.scheduled_tasks.check_free_links_indexation",
            "schedule": crontab(day_of_month="8,22", hour="5", minute="0"),
            "args": (),
        },
    },
)

# Автообнаружение задач
celery_app.autodiscover_tasks([
    "app.tasks.competitor_tasks",
    "app.tasks.link_tasks",
    "app.tasks.free_link_tasks",
    "app.tasks.alt_tag_tasks",
    "app.tasks.scheduled_tasks",
])
