"""
API — Уведомления.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    project_id: UUID | None = None,
    severity: str | None = None,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Лента уведомлений с фильтрами."""
    query = select(Notification).order_by(Notification.created_at.desc())

    if project_id:
        query = query.where(Notification.project_id == project_id)
    if severity:
        query = query.where(Notification.severity == severity)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{notification_id}/read")
async def mark_read(notification_id: UUID, db: AsyncSession = Depends(get_db)):
    """Отметить уведомление прочитанным."""
    notif = await db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(404, "Уведомление не найдено")
    notif.is_read = True
    await db.commit()
    return {"status": "ok"}
