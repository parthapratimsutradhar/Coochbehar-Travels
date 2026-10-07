"""Socket.IO event manager — THE single source of truth for all socket events.

IMPORTANT: socket_service.py should only contain broadcast helper functions,
NOT @sio.event decorators.  Having decorators in both files caused duplicate
handler registration (socket_service overwrote socket_manager handlers on import).
This file is the only place that registers socket event handlers.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import socketio
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.enums import AccountRole
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
    upsert_active_visitor,
)
from app.utils.cdn_urls import cdn_url_for_value
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# ── Admin connection tracking (separate from visitor presence) ────────
# { sid -> {"actor_type": str, "actor_id": str} }
_admin_sessions: dict[str, dict[str, str]] = {}
# Track all tabs/windows for each admin or staff account so presence only
# flips offline after the last socket for that account disconnects.
_admin_connections: dict[str, set[str]] = {}


def _safe_uuid(value: Any) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _touch_visitor_last_seen(visitor_id: str) -> None:
    db_visitor_id = _safe_uuid(visitor_id)
    if not db_visitor_id:
        return

    from app.repository.visitor_repo import VisitorRepository

    db = SessionLocal()
    try:
        VisitorRepository(db).update_last_seen(db_visitor_id)
    except Exception:
        logger.exception("Failed to update last-seen time for visitor %s", visitor_id)
    finally:
        db.close()


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
        "customer_email": record.get("customer_email"),
        "customer_mobile": record.get("customer_mobile"),
        "customer_profile_pic": record.get("customer_profile_pic"),
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


async def _broadcast_live_stats(
    *, sid: str | None = None, include_visitors: bool = True
) -> None:
    """Send a targeted presence snapshot or compact counts to all admins."""
    counts = get_live_counts()
    payload = {
        **counts,
        "timestamp": _now_iso(),
    }
    if include_visitors:
        payload["active_visitors"] = list(ACTIVE_VISITORS.values())
    room = sid or ADMIN_REALTIME_ROOM
    try:
        await sio.emit("live_stats", payload, room=room)
    except Exception:
        logger.exception("Failed to broadcast live_stats")


async def _broadcast(event_name: str, payload: dict[str, Any]) -> None:
    try:
        await sio.emit(event_name, payload, room=ADMIN_REALTIME_ROOM)
    except Exception:
        logger.exception("Failed to emit %s to admin room", event_name)


def _load_visitor_identity(
    visitor_id: uuid.UUID,
) -> tuple[str | None, dict[str, str | None] | None]:
    from app.models.visitor import Visitor

    db = SessionLocal()
    try:
        visitor = db.scalar(
            select(Visitor)
            .options(joinedload(Visitor.customer))
            .where(Visitor.id == visitor_id)
        )
        if visitor is None:
            return None, None
        customer = visitor.customer
        if customer is None or customer.role != AccountRole.CUSTOMER:
            return visitor.visitor_code, None
        return visitor.visitor_code, {
            "customer_id": str(customer.id),
            "customer_name": customer.name,
            "customer_email": customer.email,
            "customer_mobile": customer.mobile,
            "customer_profile_pic": cdn_url_for_value(customer.profile_pic)
            if customer.profile_pic
            else None,
        }
    except Exception:
        logger.exception("Failed to load visitor identity from database")
        return None, None
    finally:
        db.close()


async def _broadcast_admin_presence(
    *, actor_type: str, actor_id: str, online: bool
) -> None:
    """Notify the admin room when an account's first/last socket changes."""
    await sio.emit(
        "presence.updated",
        {
            "actor_type": actor_type,
            "actor_id": actor_id,
            "online": online,
            "timestamp": _now_iso(),
        },
        room=ADMIN_REALTIME_ROOM,
    )


def _resolve_visitor_id(sid: str, data: dict[str, Any]) -> str:
    """Resolve the socket's canonical visitor id.

    Once connected, the server-side socket index is authoritative. This keeps
    a client from changing another visitor's live presence by including an
    arbitrary visitor_id in a later event payload.
    """
    return str(VISITOR_SOCKET_INDEX.get(sid) or data.get("visitor_id") or data.get("visitorId") or uuid.uuid4())


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

        actor_id_str = str(actor_id)
        actor_key = f"{actor_type}:{actor_id_str}"
        first_connection = actor_key not in _admin_connections
        _admin_sessions[sid] = {"actor_type": actor_type, "actor_id": actor_id_str}
        _admin_connections.setdefault(actor_key, set()).add(sid)
        await sio.save_session(sid, {"actor_type": actor_type, "actor_id": str(actor_id)})
        await sio.enter_room(sid, ADMIN_REALTIME_ROOM)
        await sio.enter_room(sid, ANALYTICS_REALTIME_ROOM)
        await sio.enter_room(sid, f"{actor_type}:{actor_id}")
        if first_connection:
            await _broadcast_admin_presence(
                actor_type=actor_type,
                actor_id=actor_id_str,
                online=True,
            )
        logger.debug("Admin %s connected (sid=%s)", actor_id, sid)
        # Send current live stats snapshot immediately
        await _broadcast_live_stats(sid=sid)
        return True

    # ── Visitor / Customer path ───────────────────────────────────────
    visitor_id = str(handshake.get("visitor_id") or handshake.get("visitorId") or uuid.uuid4())
    session_id = handshake.get("session_id") or handshake.get("sessionId")
    visitor_code: str | None = None
    customer_data: dict[str, str | None] | None = None
    db_visitor_id = _safe_uuid(visitor_id)
    if db_visitor_id:
        visitor_code, customer_data = _load_visitor_identity(db_visitor_id)
    customer_data = customer_data or {}
    customer_id = customer_data.get("customer_id")

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
        customer_name=customer_data.get("customer_name"),
        customer_email=customer_data.get("customer_email"),
        customer_mobile=customer_data.get("customer_mobile"),
        customer_profile_pic=customer_data.get("customer_profile_pic"),
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
    await _broadcast_live_stats(include_visitors=False)

    logger.debug("Visitor %s connected (sid=%s, type=%s)", visitor_id, sid, record.get("visitor_type"))
    return True


# ── Disconnect ────────────────────────────────────────────────────────

@sio.event
async def disconnect(sid: str) -> None:
    # Admin/Staff disconnect
    admin_session = _admin_sessions.pop(sid, None)
    if admin_session:
        actor_type = admin_session["actor_type"]
        actor_id = admin_session["actor_id"]
        actor_key = f"{actor_type}:{actor_id}"
        connections = _admin_connections.get(actor_key, set())
        connections.discard(sid)
        if connections:
            _admin_connections[actor_key] = connections
        else:
            _admin_connections.pop(actor_key, None)
            await _broadcast_admin_presence(
                actor_type=actor_type,
                actor_id=actor_id,
                online=False,
            )
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
    _touch_visitor_last_seen(visitor_id)
    if record:
        payload = {
            "visitor_id": visitor_id,
            "visitor_type": record.get("visitor_type", "visitor"),
            "session_id": record.get("session_id"),
            "last_activity": record.get("last_activity"),
        }
        await _broadcast("visitor_disconnected", payload)

    await _broadcast_live_stats(include_visitors=False)
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

    visitor_code: str | None = None
    customer_data: dict[str, str | None] | None = None
    db_vid = _safe_uuid(visitor_id)
    if db_vid:
        visitor_code, customer_data = _load_visitor_identity(db_vid)
    customer_data = customer_data or {}
    customer_id = customer_data.get("customer_id")

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
        customer_name=customer_data.get("customer_name"),
        customer_email=customer_data.get("customer_email"),
        customer_mobile=customer_data.get("customer_mobile"),
        customer_profile_pic=customer_data.get("customer_profile_pic"),
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

    current_session = await sio.get_session(sid)
    await sio.save_session(
        sid,
        {
            **(current_session if isinstance(current_session, dict) else {}),
            "visitor_id": visitor_id,
            "session_id": record.get("session_id"),
        },
    )
    await sio.enter_room(sid, f"{VISITOR_REALTIME_ROOM_PREFIX}{visitor_id}")
    await _broadcast("visitor_identified", _build_visitor_payload(visitor_id))
    await _broadcast_live_stats()


@sio.event
async def page_view(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = _resolve_visitor_id(sid, data)
    page = data.get("path") or data.get("page") or data.get("url")
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=page,
        current_url=data.get("current_url") or data.get("currentUrl") or page,
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
    visitor_id = _resolve_visitor_id(sid, data)
    page = data.get("path") or data.get("page") or data.get("url")
    record = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=page,
        current_url=data.get("current_url") or data.get("currentUrl") or page,
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
    visitor_id = _resolve_visitor_id(sid, data)
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
    visitor_id = _resolve_visitor_id(sid, data)
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
    visitor_id = _resolve_visitor_id(sid, data)
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
    visitor_id = _resolve_visitor_id(sid, data)
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
        await _broadcast_live_stats(sid=sid)


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