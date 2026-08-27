import argparse
import logging
from datetime import datetime, timedelta, timezone

import cloudinary
import cloudinary.api
from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# Configuration

TEMP_FOLDER = "Coochbehar-travels/temporary-uploads/"

TEMP_RETENTION = 1
TEMP_RETENTION_UNIT = "day"  # minute, hour, day, month

BATCH_SIZE = 100

TIMEZONE = "Asia/Kolkata"


# Retention

def get_retention_cutoff():
    now = datetime.now(timezone.utc)

    if TEMP_RETENTION <= 0:
        raise ValueError("TEMP_RETENTION must be greater than 0.")

    if TEMP_RETENTION_UNIT == "minute":
        return now - timedelta(minutes=TEMP_RETENTION)

    if TEMP_RETENTION_UNIT == "hour":
        return now - timedelta(hours=TEMP_RETENTION)

    if TEMP_RETENTION_UNIT == "day":
        return now - timedelta(days=TEMP_RETENTION)

    if TEMP_RETENTION_UNIT == "month":
        # Calendar-month subtraction.
        month = now.month - TEMP_RETENTION
        year = now.year

        while month <= 0:
            month += 12
            year -= 1

        # Handle dates that don't exist in the target month.
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        day = min(now.day, last_day)

        return now.replace(
            year=year,
            month=month,
            day=day,
        )

    raise ValueError(
        "Invalid TEMP_RETENTION_UNIT. "
        "Use: minute, hour, day, or month."
    )


def get_cleanup_expression():
    cutoff = get_retention_cutoff()

    # Cloudinary expects the timestamp in UTC.
    cutoff_string = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    return f'folder:"{TEMP_FOLDER}" AND created_at<"{cutoff_string}"'


# Cleanup

def cleanup_cloudinary_temp_files():
    expression = get_cleanup_expression()

    logger.info(
        "Starting Cloudinary temporary-file cleanup. "
        "Retention: %d %s",
        TEMP_RETENTION,
        TEMP_RETENTION_UNIT,
    )

    logger.info("Search expression: %s", expression)

    next_cursor = None
    total_deleted = 0

    while True:
        search = (
            cloudinary.Search()
            .expression(expression)
            .max_results(BATCH_SIZE)
        )

        if next_cursor:
            search = search.next_cursor(next_cursor)

        result = search.execute()

        resources = result.get("resources", [])

        if not resources:
            break

        for resource_type in ("image", "video", "raw"):
            public_ids = [
                resource["public_id"]
                for resource in resources
                if resource["resource_type"] == resource_type
            ]

            if not public_ids:
                continue

            cloudinary.api.delete_resources(
                public_ids,
                resource_type=resource_type,
                type="upload",
            )

            total_deleted += len(public_ids)

            logger.info(
                "Deleted %d %s assets",
                len(public_ids),
                resource_type,
            )

        next_cursor = result.get("next_cursor")

        if not next_cursor:
            break

    logger.info(
        "Cloudinary cleanup finished. Total deleted: %d",
        total_deleted,
    )

# Scheduler

def run_scheduler():
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        cleanup_cloudinary_temp_files,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup-cloudinary-temp-files",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    logger.info(
        "Cloudinary cleanup scheduler started. "
        "Daily at 03:00 (%s).",
        TIMEZONE,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Cloudinary cleanup scheduler stopped.")

# CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean up expired temporary Cloudinary uploads."
    )

    mode = parser.add_mutually_exclusive_group(required=True)

    mode.add_argument(
        "--run-now",
        action="store_true",
        help="Run the cleanup once and exit.",
    )

    mode.add_argument(
        "--schedule",
        action="store_true",
        help="Run the cleanup every day at 03:00 Asia/Kolkata.",
    )

    args = parser.parse_args()

    if args.run_now:
        cleanup_cloudinary_temp_files()

    elif args.schedule:
        run_scheduler()
        

"""
# Manual cleanup:
    uv run python scripts/cleanup_cloudinary_temp.py --run-now
    
# Schedule cleanup:
    uv run python scripts/cleanup_cloudinary_temp.py --schedule 
"""        