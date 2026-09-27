from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


ACTIVE_VISITORS: dict[str, dict[str, Any]] = {}
VISITOR_SOCKETS: dict[str, set[str]] = defaultdict(set)
VISITOR_SOCKET_INDEX: dict[str, str] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_active_visitor(
    *,
    visitor_id: str,
    session_id: str | None = None,
    customer_id: str | None = None,
    is_anonymous: bool = True,
    page: str | None = None,
    previous_page: str | None = None,
    activity: str | None = None,
    source: str | None = None,
    current_url: str | None = None,
    device: str | None = None,
    browser: str | None = None,
    os: str | None = None,
    ip_address: str | None = None,
    country: str | None = None,
    city: str | None = None,
    referrer: str | None = None,
    session_start: str | None = None,
    last_activity: str | None = None,
) -> dict[str, Any]:
    record = ACTIVE_VISITORS.setdefault(
        visitor_id,
        {
            "visitor_id": visitor_id,
            "session_id": session_id,
            "customer_id": customer_id,
            "is_anonymous": is_anonymous,
            "page": page,
            "previous_page": previous_page,
            "activity": activity,
            "source": source,
            "current_url": current_url,
            "device": device,
            "browser": browser,
            "os": os,
            "ip_address": ip_address,
            "country": country,
            "city": city,
            "referrer": referrer,
            "session_start": session_start or _now_iso(),
            "last_activity": last_activity or _now_iso(),
            "connected_at": _now_iso(),
            "is_active": True,
        },
    )

    if session_id is not None:
        record["session_id"] = session_id
    if customer_id is not None:
        record["customer_id"] = customer_id
    record["is_anonymous"] = is_anonymous
    if page is not None:
        record["previous_page"] = record.get("page")
        record["page"] = page
    if activity is not None:
        record["activity"] = activity
    if source is not None:
        record["source"] = source
    if current_url is not None:
        record["current_url"] = current_url
    if device is not None:
        record["device"] = device
    if browser is not None:
        record["browser"] = browser
    if os is not None:
        record["os"] = os
    if ip_address is not None:
        record["ip_address"] = ip_address
    if country is not None:
        record["country"] = country
    if city is not None:
        record["city"] = city
    if referrer is not None:
        record["referrer"] = referrer
    record["last_activity"] = _now_iso()
    return record


def remove_active_visitor(visitor_id: str) -> None:
    global VISITOR_SOCKET_INDEX
    ACTIVE_VISITORS.pop(visitor_id, None)
    VISITOR_SOCKET_INDEX = {sid: vid for sid, vid in VISITOR_SOCKET_INDEX.items() if vid != visitor_id}
