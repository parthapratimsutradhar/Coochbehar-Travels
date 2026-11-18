import asyncio
import logging

from app.db.database import SessionLocal
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


async def run_referral_reward_check() -> dict[str, int]:
    return await asyncio.to_thread(_run_referral_reward_check)


def _run_referral_reward_check() -> dict[str, int]:
    db = SessionLocal()
    try:
        summary = ReferralService(db).process_eligible_rewards()
        logger.info(
            "Referral reward check completed: %d credited, %d skipped, %d failed",
            summary["credited"],
            summary["skipped"],
            summary["failed"],
        )
        return summary
    except Exception:
        logger.exception("Referral reward check failed")
        db.rollback()
        raise
    finally:
        db.close()
