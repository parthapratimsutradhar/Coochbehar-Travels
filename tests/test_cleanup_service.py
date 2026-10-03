import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.core.config import settings
from app.services import cleanup_service
from app.services.cleanup_service import _cutoff, next_cleanup_run


def test_cutoff_uses_configured_retention_days(monkeypatch):
    monkeypatch.setattr(settings, "DATA_RETENTION_DAYS", 30)
    cutoff = _cutoff()

    elapsed = datetime.now(timezone.utc) - cutoff
    assert timedelta(days=30) <= elapsed < timedelta(days=30, seconds=1)


def test_next_cleanup_run_uses_configured_local_hour(monkeypatch):
    monkeypatch.setattr(settings, "CLEANUP_TIMEZONE", "Asia/Kolkata")
    now = datetime(2026, 10, 3, 2, 30, tzinfo=ZoneInfo("Asia/Kolkata"))

    assert next_cleanup_run(1, 3, 0, now) == datetime(
        2026, 10, 3, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata")
    )


def test_next_cleanup_run_moves_to_tomorrow_after_scheduled_time(monkeypatch):
    monkeypatch.setattr(settings, "CLEANUP_TIMEZONE", "Asia/Kolkata")
    now = datetime(2026, 10, 3, 4, 1, tzinfo=ZoneInfo("Asia/Kolkata"))

    assert next_cleanup_run(1, 4, 0, now) == datetime(
        2026, 10, 4, 4, 0, tzinfo=ZoneInfo("Asia/Kolkata")
    )


def test_next_cleanup_run_respects_multi_day_interval(monkeypatch):
    timezone = ZoneInfo("Asia/Kolkata")
    anchor = datetime(1970, 1, 1, tzinfo=timezone)
    monkeypatch.setattr(settings, "CLEANUP_TIMEZONE", "Asia/Kolkata")
    now = anchor + timedelta(days=10, hours=2)

    assert next_cleanup_run(3, 3, 0, now) == anchor + timedelta(days=12, hours=3)


def test_next_cleanup_run_supports_weekly_cdn_schedule(monkeypatch):
    timezone = ZoneInfo("Asia/Kolkata")
    anchor = datetime(1970, 1, 1, tzinfo=timezone)
    monkeypatch.setattr(settings, "CLEANUP_TIMEZONE", "Asia/Kolkata")
    now = anchor + timedelta(days=10, hours=2)

    assert next_cleanup_run(7, 3, 0, now) == anchor + timedelta(days=14, hours=3)


def test_run_cleanup_only_deletes_temporary_cdn_files(monkeypatch):
    monkeypatch.setattr(
        "app.services.cdn_service.cleanup_expired_temp_uploads", lambda: 4
    )
    monkeypatch.setattr(
        cleanup_service,
        "SessionLocal",
        lambda: pytest.fail("CDN cleanup must not open an analytics session"),
    )

    result = asyncio.run(cleanup_service.run_cleanup())

    assert result == {"temp_files_deleted": 4}


def test_analytics_cleanup_does_not_delete_temporary_cdn_files(monkeypatch):
    db = SimpleNamespace(close=lambda: None, rollback=lambda: None)
    monkeypatch.setattr(cleanup_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        cleanup_service, "cleanup_old_data", lambda session: {"events_deleted": 2}
    )
    monkeypatch.setattr(
        "app.services.cdn_service.cleanup_expired_temp_uploads",
        lambda: pytest.fail("Analytics cleanup must not delete CDN files"),
    )

    result = asyncio.run(cleanup_service.run_analytics_cleanup())

    assert result == {"events_deleted": 2}