import asyncio
import logging

from app.db.database import SessionLocal
from app.services.quotation_service import QuotationService

logger = logging.getLogger(__name__)


async def run_quotation_expiry_check() -> dict[str, int]:
    return await asyncio.to_thread(_run_quotation_expiry_check)


def _run_quotation_expiry_check() -> dict[str, int]:
    db = SessionLocal()
    try:
        expired_count = QuotationService(db).expire_due_quotations()
        logger.info("Quotation expiry check completed: %d expired", expired_count)
        return {"expired": expired_count}
    except Exception:
        logger.exception("Quotation expiry check failed")
        db.rollback()
        raise
    finally:
        db.close()
