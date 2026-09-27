"""90-day data retention cleanup service.

Scheduled to run once daily.  Deletes visitor_events, visitor_sessions,
and visitors whose data is older than 90 days, in the correct FK order.

Usage (called from app startup lifespan):
    from app.services.cleanup_service import run_cleanup
    await run_cleanup()
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)


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


async def run_cleanup() -> dict[str, int]:
    """Async wrapper — opens its own DB session and runs cleanup."""
    db = SessionLocal()
    try:
        return cleanup_old_data(db)
    except Exception:
        logger.exception("Analytics cleanup failed")
        db.rollback()
        return {"events_deleted": 0, "sessions_deleted": 0, "visitors_deleted": 0, "error": True}
    finally:
        db.close()
