import asyncio
from datetime import datetime, timezone
from importlib import import_module

from app.scheduler import cleanup_service

main = import_module("app.main")


def test_calendar_runner_invokes_the_supplied_job(monkeypatch):
    calls = []
    sleep_calls = 0

    async def job():
        calls.append(True)
        return {"completed": 1}

    async def fake_sleep(_delay):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 1:
            raise asyncio.CancelledError

    monkeypatch.setattr(
        cleanup_service,
        "next_cleanup_run",
        lambda *_args: datetime.now(timezone.utc),
    )
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(main._scheduled_calendar_task("test job", job, 1, 0, 0))
    except asyncio.CancelledError:
        pass

    assert calls == [True]
