"""In-memory presence store for live visitor tracking.

Each active visitor occupies one entry in ACTIVE_VISITORS keyed by
visitor_id (string UUID from the visitors table).  Multiple browser tabs
from the same visitor share a single entry; tab count is tracked via
VISITOR_SOCKETS.

Fields stored per visitor:
  visitor_id      – UUID string of the Visitor DB record
  session_id      – UUID string of the current VisitorSession
  customer_id     – UUID string if visitor is a logged-in customer, else None
  visitor_type    – "customer" | "visitor"  (for admin filter)
  visitor_code    – Short human-readable code (e.g. VIS-ABC123)
  customer_name   – Full name if customer, else None
  page            – Current page path/URL
  previous_page   – Previous page path/URL
  activity        – Last activity label
  source          – Traffic source (direct/referral/organic/social/paid)
  utm_source      – UTM source param
  utm_medium      – UTM medium param
  utm_campaign    – UTM campaign param
  utm_term        – UTM term param
  utm_content     – UTM content param
  referrer        – Raw HTTP referrer URL
  current_url     – Full current URL
  device          – Device type (mobile/desktop/tablet)
  browser         – Browser name/version
  os              – Operating system
  ip_address      – IP address
  country         – Country name
  state           – State/province
  city            – City name
  session_start   – ISO timestamp when session began
  connected_at    – ISO timestamp when socket connected
  last_activity   – ISO timestamp of last event
  is_active       – True while at least one socket is open
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


# ── Shared state ──────────────────────────────────────────────────────
# { visitor_id: {presence_dict} }
ACTIVE_VISITORS: dict[str, dict[str, Any]] = {}

# { visitor_id: {sid, sid, ...} }  — one entry per open tab
VISITOR_SOCKETS: dict[str, set[str]] = defaultdict(set)

# { sid: visitor_id }  — reverse index for fast disconnect lookup
VISITOR_SOCKET_INDEX: dict[str, str] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Presence helpers ──────────────────────────────────────────────────

def upsert_active_visitor(
    *,
    visitor_id: str,
    session_id: str | None = None,
    customer_id: str | None = None,
    visitor_type: str | None = None,       # "customer" | "visitor"
    visitor_code: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_mobile: str | None = None,
    customer_profile_pic: str | None = None,
    is_anonymous: bool = True,
    page: str | None = None,
    previous_page: str | None = None,
    activity: str | None = None,
    source: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    referrer: str | None = None,
    current_url: str | None = None,
    device: str | None = None,
    browser: str | None = None,
    os: str | None = None,
    ip_address: str | None = None,
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    session_start: str | None = None,
    last_activity: str | None = None,
) -> dict[str, Any]:
    """Upsert presence for a visitor.  Creates the record on first call,
    then merges non-None fields on subsequent calls.
    """
    record = ACTIVE_VISITORS.setdefault(
        visitor_id,
        {
            "visitor_id": visitor_id,
            "session_id": session_id,
            "customer_id": customer_id,
            "visitor_type": visitor_type or ("customer" if customer_id else "visitor"),
            "visitor_code": visitor_code,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_mobile": customer_mobile,
            "customer_profile_pic": customer_profile_pic,
            "is_anonymous": is_anonymous,
            "page": page,
            "previous_page": previous_page,
            "activity": activity,
            "source": source,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "utm_term": utm_term,
            "utm_content": utm_content,
            "referrer": referrer,
            "current_url": current_url,
            "device": device,
            "browser": browser,
            "os": os,
            "ip_address": ip_address,
            "country": country,
            "state": state,
            "city": city,
            "session_start": session_start or _now_iso(),
            "last_activity": last_activity or _now_iso(),
            "connected_at": _now_iso(),
            "is_active": True,
        },
    )

    # Merge non-None updates
    if session_id is not None:
        record["session_id"] = session_id
    if customer_id is not None:
        record["customer_id"] = customer_id
        record["visitor_type"] = "customer"
        record["is_anonymous"] = False
    if visitor_type is not None:
        record["visitor_type"] = visitor_type
    if visitor_code is not None:
        record["visitor_code"] = visitor_code
    if customer_name is not None:
        record["customer_name"] = customer_name
    if customer_email is not None:
        record["customer_email"] = customer_email
    if customer_mobile is not None:
        record["customer_mobile"] = customer_mobile
    if customer_profile_pic is not None:
        record["customer_profile_pic"] = customer_profile_pic
    # is_anonymous always updated
    record["is_anonymous"] = is_anonymous

    if page is not None:
        record["previous_page"] = record.get("page")
        record["page"] = page
    if activity is not None:
        record["activity"] = activity
    if source is not None:
        record["source"] = source
    if utm_source is not None:
        record["utm_source"] = utm_source
    if utm_medium is not None:
        record["utm_medium"] = utm_medium
    if utm_campaign is not None:
        record["utm_campaign"] = utm_campaign
    if utm_term is not None:
        record["utm_term"] = utm_term
    if utm_content is not None:
        record["utm_content"] = utm_content
    if referrer is not None:
        record["referrer"] = referrer
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
    if state is not None:
        record["state"] = state
    if city is not None:
        record["city"] = city

    record["last_activity"] = _now_iso()
    record["is_active"] = True
    return record


def remove_active_visitor(visitor_id: str) -> None:
    """Remove a visitor from the presence store and clean socket indexes."""
    global VISITOR_SOCKET_INDEX
    ACTIVE_VISITORS.pop(visitor_id, None)
    VISITOR_SOCKET_INDEX = {
        sid: vid for sid, vid in VISITOR_SOCKET_INDEX.items() if vid != visitor_id
    }


# ── Live count helpers ────────────────────────────────────────────────

def get_live_counts() -> dict[str, int]:
    """Return live visitor/customer counts from the in-memory store."""
    total = len(ACTIVE_VISITORS)
    customers = sum(
        1 for v in ACTIVE_VISITORS.values()
        if v.get("visitor_type") == "customer" or v.get("customer_id")
    )
    return {
        "total": total,
        "customers": customers,
        "visitors": total - customers,
    }



