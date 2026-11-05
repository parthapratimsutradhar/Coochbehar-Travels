import asyncio
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.booking import Booking
from app.models.document import Document
from app.services.cdn_service import delete_private_document_file

logger = logging.getLogger(__name__)

DOCUMENT_RETENTION_AFTER_RETURN_DAYS = 10


def cleanup_expired_booking_documents(
    db: Session,
    today: date | None = None,
) -> dict[str, int]:
    """Permanently remove booking documents ten days after their return date."""
    current_date = today or datetime.now(ZoneInfo(settings.CLEANUP_TIMEZONE)).date()
    cutoff_date = current_date - timedelta(
        days=DOCUMENT_RETENTION_AFTER_RETURN_DAYS
    )
    documents = db.execute(
        select(Document)
        .join(Booking, Document.booking_id == Booking.id)
        .where(Booking.return_date <= cutoff_date)
    ).scalars().all()

    documents_deleted = 0
    files_deleted = 0
    for document in documents:
        try:
            file_deleted = delete_private_document_file(document.file_url)
        except (HTTPException, OSError):
            logger.exception(
                "Could not delete expired booking document %s; retaining its record",
                document.id,
            )
            continue

        db.delete(document)
        documents_deleted += 1
        files_deleted += int(file_deleted)

    db.commit()
    summary = {
        "documents_deleted": documents_deleted,
        "files_deleted": files_deleted,
    }
    logger.info(
        "Expired booking document cleanup complete: %d documents and %d files removed (return date cutoff=%s)",
        documents_deleted,
        files_deleted,
        cutoff_date,
    )
    return summary


async def run_booking_document_cleanup() -> dict[str, int]:
    """Open a database session and remove expired booking documents."""
    return await asyncio.to_thread(_run_booking_document_cleanup)


def _run_booking_document_cleanup() -> dict[str, int]:
    db = SessionLocal()
    try:
        return cleanup_expired_booking_documents(db)
    except Exception:
        logger.exception("Expired booking document cleanup failed")
        db.rollback()
        raise
    finally:
        db.close()
