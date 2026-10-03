"""Configurable data-retention cleanup service.

Runs at the configured interval. Deletes analytics data older than the
configured retention period, and expired temporary CDN uploads.

Usage (called by the scheduled cleanup task):
    from app.services.cleanup_service import run_cleanup
    await run_cleanup()
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import asyncio

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession

logger = logging.getLogger(__name__)

RETENTION_DAYS = settings.DATA_RETENTION_DAYS


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=settings.DATA_RETENTION_DAYS)


def next_cleanup_run(
    interval_days: int,
    hour: int,
    minute: int,
    now: datetime | None = None,
) -> datetime:
    cleanup_timezone = ZoneInfo(settings.CLEANUP_TIMEZONE)
    current_time = now or datetime.now(cleanup_timezone)
    if current_time.tzinfo is None:
        raise ValueError("Cleanup scheduling requires a timezone-aware datetime")
    if interval_days < 1:
        raise ValueError("Cleanup interval must be at least one day")
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Cleanup time must be a valid hour and minute")
    current_time = current_time.astimezone(cleanup_timezone)

    anchor_date = date(1970, 1, 1)
    days_since_anchor = (current_time.date() - anchor_date).days
    days_until_run = (-days_since_anchor) % interval_days
    scheduled_date = current_time.date() + timedelta(days=days_until_run)
    scheduled_time = datetime.combine(scheduled_date, current_time.timetz()).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if scheduled_time < current_time:
        scheduled_time += timedelta(days=interval_days)
    return scheduled_time


def cleanup_old_data(db: Session) -> dict[str, int]:
    """Delete analytics data older than RETENTION_DAYS.

    Deletion order matters (FK cascade):
      1. visitor_events  (FK -> visitor_sessions)
      2. visitor_sessions (FK -> visitors)
      3. visitors with no remaining sessions and last_seen < cutoff
    """
    cutoff = _cutoff()

    # 1. Delete stale events
    events_stmt = delete(VisitorEvent).where(VisitorEvent.created_at < cutoff)
    events_result = db.execute(events_stmt)
    events_deleted = events_result.rowcount or 0

    # 2. Delete stale sessions (ended before cutoff OR started before cutoff and never ended)
    sessions_stmt = delete(VisitorSession).where(
        (VisitorSession.started_at < cutoff)
    )
    sessions_result = db.execute(sessions_stmt)
    sessions_deleted = sessions_result.rowcount or 0

    # 3. Delete visitors with last_seen before cutoff and no recent sessions
    #    (a visitor might have recent sessions even if old events were pruned)
    stale_visitor_subq = (
        select(Visitor.id)
        .where(Visitor.last_seen < cutoff)
        .scalar_subquery()
    )
    visitors_stmt = delete(Visitor).where(Visitor.id.in_(stale_visitor_subq))
    visitors_result = db.execute(visitors_stmt)
    visitors_deleted = visitors_result.rowcount or 0

    db.commit()

    summary = {
        "events_deleted": events_deleted,
        "sessions_deleted": sessions_deleted,
        "visitors_deleted": visitors_deleted,
        "cutoff_date": cutoff.isoformat(),
    }
    logger.info(
        "Analytics cleanup complete: %d events, %d sessions, %d visitors removed (cutoff=%s)",
        events_deleted, sessions_deleted, visitors_deleted, cutoff.date(),
    )
    return summary


async def run_analytics_cleanup() -> dict[str, int]:
    """Open a DB session and delete analytics data beyond the retention period."""
    db = SessionLocal()
    try:
        summary = cleanup_old_data(db)
    except Exception:
        logger.exception("Analytics cleanup failed")
        db.rollback()
        summary = {"events_deleted": 0, "sessions_deleted": 0, "visitors_deleted": 0, "error": True}
    finally:
        db.close()
    return summary


async def run_cleanup() -> dict[str, int]:
    """Delete expired temporary CDN uploads without running analytics cleanup."""
    try:
        from app.services.cdn_service import cleanup_expired_temp_uploads

        deleted_count = await asyncio.to_thread(cleanup_expired_temp_uploads)
    except Exception:
        logger.exception("Temporary CDN upload cleanup failed")
        return {"temp_files_deleted": 0, "temp_files_cleanup_error": True}

    return {"temp_files_deleted": deleted_count}
