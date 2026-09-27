"""Socket.IO event manager — THE single source of truth for all socket events.

IMPORTANT: socket_service.py should only contain broadcast helper functions,
NOT @sio.event decorators.  Having decorators in both files caused duplicate
handler registration (socket_service overwrote socket_manager handlers on import).
This file is the only place that registers socket event handlers.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import socketio
from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.account import Account
from app.realtime.constants import (
    ADMIN_REALTIME_ROOM,
    ANALYTICS_REALTIME_ROOM,
    REALTIME_EVENTS,
    VISITOR_REALTIME_ROOM_PREFIX,
)
from app.realtime.presence import (
    ACTIVE_VISITORS,
    VISITOR_SOCKET_INDEX,
    VISITOR_SOCKETS,
    get_live_counts,
    remove_active_visitor,
    upsert_active_visitor,
)
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# ── Admin connection tracking (separate from visitor presence) ────────
# { sid -> {"actor_type": str, "actor_id": str} }
_admin_sessions: dict[str, dict[str, str]] = {}


def _safe_uuid(value: Any) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Payload builders ──────────────────────────────────────────────────

def _build_visitor_payload(visitor_id: str) -> dict[str, Any]:
    record = ACTIVE_VISITORS.get(visitor_id, {})
    return {
        "visitor_id": visitor_id,
        "session_id": record.get("session_id"),
        "customer_id": record.get("customer_id"),
        "visitor_type": record.get("visitor_type", "visitor"),
        "visitor_code": record.get("visitor_code"),
        "customer_name": record.get("customer_name"),
        "is_anonymous": record.get("is_anonymous", True),
        "page": record.get("page"),
        "previous_page": record.get("previous_page"),
        "activity": record.get("activity"),
        "source": record.get("source"),
        "utm_source": record.get("utm_source"),
        "utm_medium": record.get("utm_medium"),
        "utm_campaign": record.get("utm_campaign"),
        "utm_term": record.get("utm_term"),
        "utm_content": record.get("utm_content"),
        "referrer": record.get("referrer"),
        "current_url": record.get("current_url"),
        "device": record.get("device"),
        "browser": record.get("browser"),
        "os": record.get("os"),
        "ip_address": record.get("ip_address"),
        "country": record.get("country"),
        "state": record.get("state"),
        "city": record.get("city"),
        "session_start": record.get("session_start"),
        "last_activity": record.get("last_activity"),
        "connected_at": record.get("connected_at"),
    }


async def _broadcast_live_stats() -> None:
    """Push current live visitor/customer counts to all admin sockets."""
    counts = get_live_counts()
    payload = {
        **counts,
        "active_visitors": list(ACTIVE_VISITORS.values()),
        "timestamp": _now_iso(),
    }
    try:
        await sio.emit("live_stats", payload, room=ADMIN_REALTIME_ROOM)
    except Exception:
        logger.exception("Failed to broadcast live_stats")
    try:
        await sio.emit("live_stats", payload, room=ANALYTICS_REALTIME_ROOM)
    except Exception:
        logger.exception("Failed to broadcast live_stats to analytics room")


async def _broadcast(event_name: str, payload: dict[str, Any]) -> None:
    for room in [ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM]:
        try:
            await sio.emit(event_name, payload, room=room)
        except Exception:
            logger.exception("Failed to emit %s to %s", event_name, room)


# ── Helper: classify traffic source ──────────────────────────────────

def _classify_source(referrer: str | None, utm_source: str | None, utm_medium: str | None) -> str:
    """Determine traffic source label from referrer + UTM params."""
    if utm_source or utm_medium:
        medium = (utm_medium or "").lower()
        source = (utm_source or "").lower()
        if medium in ("cpc", "ppc", "paid", "paidsearch", "paid_social", "paidads"):
            return "paid"
        if medium in ("email", "newsletter"):
            return "email"
        if medium == "social" or source in ("facebook", "instagram", "twitter", "linkedin", "tiktok", "youtube", "pinterest", "snapchat"):
            return "social"
        if medium in ("organic", "seo"):
            return "organic"
        return "utm_campaign"

    if not referrer:
        return "direct"

    referrer_lower = referrer.lower()
    # Search engines
    search_engines = ("google.", "bing.", "yahoo.", "duckduckgo.", "baidu.", "yandex.", "ask.com", "msn.com")
    for se in search_engines:
        if se in referrer_lower:
            return "organic"

    # Social
    social_domains = ("facebook.com", "instagram.com", "twitter.com", "t.co", "linkedin.com",
                      "tiktok.com", "youtube.com", "pinterest.com", "snapchat.com", "reddit.com")
    for sd in social_domains:
        if sd in referrer_lower:
            return "social"

    return "referral"


# ── Connect ───────────────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> bool:
    """Handle new socket connection.

    Admin/Staff: authenticate via JWT, join ADMIN room.
    Visitor/Customer: register in presence store, notify admin.
    """
    handshake = auth or {}
    token = handshake.get("token")
    jwt_payload = decode_access_token(token) if token else None
    actor_type = (jwt_payload or {}).get("role", "").upper() if jwt_payload else ""
    subject = (jwt_payload or {}).get("sub") if jwt_payload else None

    # ── Admin / Staff path ────────────────────────────────────────────
    if actor_type in {"ADMIN", "STAFF"} and subject:
        actor_id = _safe_uuid(subject)
        if not actor_id:
            return False
        db = SessionLocal()
        try:
            valid = db.scalar(
                select(Account.id).where(Account.id == actor_id, Account.is_active.is_(True))
            )
            if not valid:
                return False
        finally:
            db.close()

        _admin_sessions[sid] = {"actor_type": actor_type, "actor_id": str(actor_id)}
        await sio.save_session(sid, {"actor_type": actor_type, "actor_id": str(actor_id)})
        await sio.enter_room(sid, ADMIN_REALTIME_ROOM)
        await sio.enter_room(sid, ANALYTICS_REALTIME_ROOM)
        await sio.enter_room(sid, f"{actor_type}:{actor_id}")
        logger.debug("Admin %s connected (sid=%s)", actor_id, sid)
        # Send current live stats snapshot immediately
        await _broadcast_live_stats()
        return True

    # ── Visitor / Customer path ───────────────────────────────────────
    visitor_id = str(handshake.get("visitor_id") or handshake.get("visitorId") or uuid.uuid4())
    session_id = handshake.get("session_id") or handshake.get("sessionId")
    customer_id = handshake.get("customer_id") or handshake.get("customerId")

    # Optionally look up extra visitor data from DB
    visitor_code: str | None = None
    customer_name: str | None = None
    db_visitor_id = _safe_uuid(visitor_id)
    if db_visitor_id:
        db = SessionLocal()
        try:
            from app.models.visitor import Visitor
            vis = db.scalar(select(Visitor).where(Visitor.id == db_visitor_id))
            if vis:
                visitor_code = vis.visitor_code
                if vis.customer_id and not customer_id:
                    customer_id = str(vis.customer_id)
                # Try to get customer name
                if customer_id:
                    cust = db.scalar(select(Account).where(Account.id == _safe_uuid(customer_id)))
                    if cust:
                        customer_name = cust.name
        except Exception:
            logger.exception("Failed to look up visitor from DB during connect")
        finally:
            db.close()

    referrer = handshake.get("referrer")
    utm_source = handshake.get("utm_source") or handshake.get("utmSource")
    utm_medium = handshake.get("utm_medium") or handshake.get("utmMedium")
    utm_campaign = handshake.get("utm_campaign") or handshake.get("utmCampaign")
    utm_term = handshake.get("utm_term") or handshake.get("utmTerm")
    utm_content = handshake.get("utm_content") or handshake.get("utmContent")
    source = handshake.get("source") or _classify_source(referrer, utm_source, utm_medium)

    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=str(session_id) if session_id else None,
        customer_id=str(customer_id) if customer_id else None,
        visitor_type="customer" if customer_id else "visitor",
        visitor_code=visitor_code,
        customer_name=customer_name,
        is_anonymous=customer_id is None,
        source=source,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_term=utm_term,
        utm_content=utm_content,
        referrer=referrer,
        current_url=handshake.get("current_url") or handshake.get("currentUrl"),
        page=handshake.get("page"),
        device=handshake.get("device"),
        browser=handshake.get("browser"),
        os=handshake.get("os"),
        ip_address=handshake.get("ip_address") or handshake.get("ipAddress"),
        country=handshake.get("country"),
        state=handshake.get("state"),
        city=handshake.get("city"),
        activity="connected",
    )

    VISITOR_SOCKETS[visitor_id].add(sid)
    VISITOR_SOCKET_INDEX[sid] = visitor_id
    await sio.save_session(sid, {"visitor_id": visitor_id, "session_id": record.get("session_id")})
    await sio.enter_room(sid, f"{VISITOR_REALTIME_ROOM_PREFIX}{visitor_id}")

    payload = _build_visitor_payload(visitor_id)
    await _broadcast("visitor_connected", payload)
    await _broadcast_live_stats()

    logger.debug("Visitor %s connected (sid=%s, type=%s)", visitor_id, sid, record.get("visitor_type"))
    return True


# ── Disconnect ────────────────────────────────────────────────────────

@sio.event
async def disconnect(sid: str) -> None:
    # Admin/Staff disconnect
    admin_session = _admin_sessions.pop(sid, None)
    if admin_session:
        logger.debug("Admin %s disconnected (sid=%s)", admin_session.get("actor_id"), sid)
        return

    # Visitor disconnect
    visitor_id = VISITOR_SOCKET_INDEX.pop(sid, None)
    if not visitor_id:
        return

    sockets = VISITOR_SOCKETS.get(visitor_id, set())
    sockets.discard(sid)

    if sockets:
        # Still has open tabs — just update activity
        return

    VISITOR_SOCKETS.pop(visitor_id, None)
    record = ACTIVE_VISITORS.pop(visitor_id, None)
    if record:
        payload = {
            "visitor_id": visitor_id,
            "visitor_type": record.get("visitor_type", "visitor"),
            "session_id": record.get("session_id"),
            "last_activity": record.get("last_activity"),
        }
        await _broadcast("visitor_disconnected", payload)

    await _broadcast_live_stats()
    logger.debug("Visitor %s disconnected (sid=%s)", visitor_id, sid)


# ── Visitor events ────────────────────────────────────────────────────

@sio.event
async def visitor_identify(sid: str, data: dict | None = None) -> None:
    """Visitor sends their DB visitor_id + optional customer_id after API identify call."""
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())

    # Update VISITOR_SOCKET_INDEX with canonical visitor_id
    old_id = VISITOR_SOCKET_INDEX.get(sid)
    if old_id and old_id != visitor_id:
        socks = VISITOR_SOCKETS.pop(old_id, set())
        VISITOR_SOCKETS[visitor_id].update(socks)
        for s in socks:
            VISITOR_SOCKET_INDEX[s] = visitor_id
        ACTIVE_VISITORS.pop(old_id, None)

    VISITOR_SOCKETS[visitor_id].add(sid)
    VISITOR_SOCKET_INDEX[sid] = visitor_id

    # Fetch visitor/customer info from DB
    visitor_code: str | None = data.get("visitor_code")
    customer_name: str | None = data.get("customer_name")
    customer_id = data.get("customer_id")
    db_vid = _safe_uuid(visitor_id)
    if db_vid and (not visitor_code or (customer_id and not customer_name)):
        db = SessionLocal()
        try:
            from app.models.visitor import Visitor
            vis = db.scalar(select(Visitor).where(Visitor.id == db_vid))
            if vis:
                visitor_code = vis.visitor_code
                if vis.customer_id and not customer_id:
                    customer_id = str(vis.customer_id)
            if customer_id:
                cust = db.scalar(select(Account).where(Account.id == _safe_uuid(customer_id)))
                if cust:
                    customer_name = cust.name
        except Exception:
            logger.exception("Failed DB lookup in visitor_identify")
        finally:
            db.close()

    referrer = data.get("referrer")
    utm_source = data.get("utm_source")
    utm_medium = data.get("utm_medium")
    utm_campaign = data.get("utm_campaign")
    utm_term = data.get("utm_term")
    utm_content = data.get("utm_content")
    source = data.get("source") or _classify_source(referrer, utm_source, utm_medium)

    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        customer_id=str(customer_id) if customer_id else None,
        visitor_type="customer" if customer_id else "visitor",
        visitor_code=visitor_code,
        customer_name=customer_name,
        is_anonymous=not bool(customer_id),
        page=data.get("page"),
        current_url=data.get("current_url"),
        source=source,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_term=utm_term,
        utm_content=utm_content,
        referrer=referrer,
        device=data.get("device"),
        browser=data.get("browser"),
        os=data.get("os"),
        ip_address=data.get("ip_address"),
        country=data.get("country"),
        state=data.get("state"),
        city=data.get("city"),
        activity="identified",
    )

    await sio.enter_room(sid, f"{VISITOR_REALTIME_ROOM_PREFIX}{visitor_id}")
    await _broadcast("visitor_identified", _build_visitor_payload(visitor_id))
    await _broadcast_live_stats()


@sio.event
async def page_view(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    page = data.get("path") or data.get("page") or data.get("url")
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=page,
        current_url=page,
        activity="page_view",
    )
    await _broadcast("page_view", {
        "event": "page_view",
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "page": page,
        "previous_page": record.get("previous_page"),
        "timestamp": _now_iso(),
    })


@sio.event
async def page_navigation(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    page = data.get("path") or data.get("page") or data.get("url")
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=page,
        current_url=page,
        activity="navigating",
    )
    await _broadcast("page_navigation", {
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "page": page,
        "previous_page": record.get("previous_page"),
        "timestamp": _now_iso(),
    })


@sio.event
async def activity(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    label = data.get("label") or data.get("activity") or "activity"
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        activity=label,
        current_url=data.get("current_url"),
    )
    await _broadcast("activity", {
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "activity": label,
        "page": record.get("page"),
        "timestamp": _now_iso(),
    })


@sio.event
async def click(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    selector = data.get("selector") or data.get("name") or data.get("element") or "button"
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        activity=f"click:{selector}",
        current_url=data.get("current_url"),
    )
    await _broadcast("click", {
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "selector": selector,
        "page": record.get("page"),
        "timestamp": _now_iso(),
    })


@sio.event
async def session_update(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=data.get("page"),
        activity=data.get("activity") or "session_update",
    )
    await _broadcast("session_updated", {
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "page": record.get("page"),
        "activity": record.get("activity"),
        "last_activity": record.get("last_activity"),
        "timestamp": _now_iso(),
    })


@sio.event
async def visitor_location_update(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        country=data.get("country"),
        state=data.get("state"),
        city=data.get("city"),
        ip_address=data.get("ip_address"),
        activity="location_update",
    )
    await _broadcast("visitor_location_updated", {
        "visitor_id": visitor_id,
        "visitor_type": record.get("visitor_type", "visitor"),
        "session_id": record.get("session_id"),
        "country": record.get("country"),
        "state": record.get("state"),
        "city": record.get("city"),
        "ip_address": record.get("ip_address"),
        "timestamp": _now_iso(),
    })


# ── Admin room management ─────────────────────────────────────────────

@sio.event
async def join_analytics(sid: str, data: dict | None = None) -> None:
    session = await sio.get_session(sid)
    if isinstance(session, dict) and session.get("actor_type") in {"ADMIN", "STAFF"}:
        await sio.enter_room(sid, ANALYTICS_REALTIME_ROOM)
        # Send immediate snapshot
        await _broadcast_live_stats()


@sio.event
async def leave_analytics(sid: str, data: dict | None = None) -> None:
    await sio.leave_room(sid, ANALYTICS_REALTIME_ROOM)


@sio.event
async def join_lead(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    lead_id = data.get("lead_id")
    if lead_id:
        await sio.enter_room(sid, f"lead:{lead_id}")
        await sio.enter_room(sid, f"sales:lead:{lead_id}")


@sio.event
async def leave_lead(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    lead_id = data.get("lead_id")
    if lead_id:
        await sio.leave_room(sid, f"lead:{lead_id}")
        await sio.leave_room(sid, f"sales:lead:{lead_id}")


@sio.event
async def join_enquiry(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    enquiry_id = data.get("enquiry_id")
    if enquiry_id:
        await sio.enter_room(sid, f"enquiry:{enquiry_id}")


@sio.event
async def leave_enquiry(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    enquiry_id = data.get("enquiry_id")
    if enquiry_id:
        await sio.leave_room(sid, f"enquiry:{enquiry_id}")


@sio.event
async def join_package(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    package_id = data.get("package_id")
    if package_id:
        await sio.enter_room(sid, f"package:{package_id}")


@sio.event
async def leave_package(sid: str, data: dict | None = None) -> None:
    if sid not in _admin_sessions or not data:
        return
    package_id = data.get("package_id")
    if package_id:
        await sio.leave_room(sid, f"package:{package_id}")


# ── Broadcast helper (used by socket_service.py) ──────────────────────

async def emit_visitor_presence_update(visitor_id: str, *, payload: dict[str, Any]) -> None:
    await _broadcast("visitor_connected", {"visitor_id": visitor_id, **payload})


__all__ = [
    "sio",
    "REALTIME_EVENTS",
    "ACTIVE_VISITORS",
    "emit_visitor_presence_update",
]
