from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
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
from app.realtime.presence import ACTIVE_VISITORS, VISITOR_SOCKET_INDEX, VISITOR_SOCKETS, upsert_active_visitor
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


def _safe_uuid(value: Any) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _build_presence_payload(visitor_id: str, *, session_id: str | None = None, **extra: Any) -> dict[str, Any]:
    record = ACTIVE_VISITORS.get(visitor_id, {})
    payload = {
        "visitor_id": visitor_id,
        "session_id": session_id or record.get("session_id"),
        "customer_id": record.get("customer_id"),
        "is_anonymous": record.get("is_anonymous", True),
        "page": record.get("page"),
        "previous_page": record.get("previous_page"),
        "activity": record.get("activity"),
        "source": record.get("source"),
        "current_url": record.get("current_url"),
        "device": record.get("device"),
        "browser": record.get("browser"),
        "os": record.get("os"),
        "ip_address": record.get("ip_address"),
        "country": record.get("country"),
        "city": record.get("city"),
        "referrer": record.get("referrer"),
        "session_start": record.get("session_start"),
        "last_activity": record.get("last_activity"),
        "connected_at": record.get("connected_at"),
    }
    payload.update(extra)
    return payload


async def _broadcast(event_name: str, payload: dict[str, Any], *, rooms: list[str] | None = None) -> None:
    target_rooms = rooms or [ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM]
    for room in target_rooms:
        try:
            await sio.emit(event_name, payload, room=room)
        except Exception:
            logger.exception("Failed to emit realtime event %s to room %s", event_name, room)


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> bool:
    handshake = auth or {}
    token = handshake.get("token")
    payload = decode_access_token(token) if token else None
    actor_type = (payload or {}).get("role", "").upper() if payload else ""
    subject = (payload or {}).get("sub") if payload else None

    visitor_id = handshake.get("visitor_id") or handshake.get("visitorId")
    session_id = handshake.get("session_id") or handshake.get("sessionId")
    customer_id = handshake.get("customer_id") or handshake.get("customerId")
    if actor_type in {"ADMIN", "STAFF"}:
        try:
            actor_id = uuid.UUID(str(subject))
        except (TypeError, ValueError):
            return False
        db = SessionLocal()
        try:
            if not db.scalar(select(Account.id).where(Account.id == actor_id, Account.is_active.is_(True))):
                return False
        finally:
            db.close()
        await sio.save_session(sid, {"actor_type": actor_type, "actor_id": str(actor_id)})
        await sio.enter_room(sid, ADMIN_REALTIME_ROOM)
        await sio.enter_room(sid, ANALYTICS_REALTIME_ROOM)
        await sio.emit(
            "presence.updated",
            {"actor_type": actor_type, "actor_id": str(actor_id), "online": True},
            room=ADMIN_REALTIME_ROOM,
        )
        return True

    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    visitor_key = str(visitor_id)
    record = upsert_active_visitor(
        visitor_id=visitor_key,
        session_id=str(session_id) if session_id else None,
        customer_id=str(customer_id) if customer_id else None,
        is_anonymous=customer_id is None,
        activity="connected",
        current_url=handshake.get("current_url"),
        source=handshake.get("source"),
        device=handshake.get("device"),
        browser=handshake.get("browser"),
        os=handshake.get("os"),
        ip_address=handshake.get("ip_address"),
        country=handshake.get("country"),
        city=handshake.get("city"),
        referrer=handshake.get("referrer"),
    )
    VISITOR_SOCKETS[visitor_key].add(sid)
    VISITOR_SOCKET_INDEX[sid] = visitor_key
    await sio.save_session(sid, {"visitor_id": visitor_key, "session_id": record.get("session_id")})
    await sio.enter_room(sid, f"{VISITOR_REALTIME_ROOM_PREFIX}{visitor_key}")
    await sio.emit(
        "visitor_connected",
        _build_presence_payload(visitor_key, session_id=record.get("session_id")),
        room=ADMIN_REALTIME_ROOM,
    )
    await sio.emit(
        "visitor_connected",
        _build_presence_payload(visitor_key, session_id=record.get("session_id")),
        room=ANALYTICS_REALTIME_ROOM,
    )
    return True


@sio.event
async def disconnect(sid: str) -> None:
    visitor_id = VISITOR_SOCKET_INDEX.pop(sid, None)
    if visitor_id is not None:
        sockets = VISITOR_SOCKETS.get(visitor_id, set())
        sockets.discard(sid)
        if not sockets:
            VISITOR_SOCKETS.pop(visitor_id, None)
            record = ACTIVE_VISITORS.get(visitor_id)
            if record:
                record["is_active"] = False
                await sio.emit(
                    "visitor_disconnected",
                    {
                        "visitor_id": visitor_id,
                        "session_id": record.get("session_id"),
                        "last_activity": record.get("last_activity"),
                    },
                    room=ADMIN_REALTIME_ROOM,
                )
                await sio.emit(
                    "visitor_disconnected",
                    {
                        "visitor_id": visitor_id,
                        "session_id": record.get("session_id"),
                        "last_activity": record.get("last_activity"),
                    },
                    room=ANALYTICS_REALTIME_ROOM,
                )
            ACTIVE_VISITORS.pop(visitor_id, None)


@sio.event
async def join_analytics(sid: str, data: dict | None = None) -> None:
    session = await sio.get_session(sid)
    actor_type = session.get("actor_type") if isinstance(session, dict) else None
    if actor_type in {"ADMIN", "STAFF"}:
        await sio.enter_room(sid, ANALYTICS_REALTIME_ROOM)


@sio.event
async def leave_analytics(sid: str, data: dict | None = None) -> None:
    await sio.leave_room(sid, ANALYTICS_REALTIME_ROOM)


@sio.event
async def visitor_identify(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        customer_id=data.get("customer_id"),
        is_anonymous=not bool(data.get("customer_id")),
        page=data.get("page"),
        current_url=data.get("current_url"),
        source=data.get("source"),
        device=data.get("device"),
        browser=data.get("browser"),
        os=data.get("os"),
        ip_address=data.get("ip_address"),
        country=data.get("country"),
        city=data.get("city"),
        referrer=data.get("referrer"),
        activity="identified",
    )
    await sio.emit("visitor_identified", {**payload}, room=ADMIN_REALTIME_ROOM)
    await sio.emit("visitor_identified", {**payload}, room=ANALYTICS_REALTIME_ROOM)


@sio.event
async def page_view(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=data.get("path") or data.get("page"),
        previous_page=data.get("previous_page"),
        activity="page_view",
        current_url=data.get("path") or data.get("page"),
        source=data.get("source"),
    )
    event_payload = {
        "event": "page_view",
        "visitor_id": visitor_id,
        "session_id": payload.get("session_id"),
        "page": payload.get("page"),
        "previous_page": payload.get("previous_page"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _broadcast("page_view", event_payload)
    await _broadcast("session_updated", {"visitor_id": visitor_id, "session_id": payload.get("session_id"), "page": payload.get("page")})


@sio.event
async def page_navigation(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=data.get("path") or data.get("page"),
        previous_page=data.get("previous_page"),
        activity="page_navigation",
    )
    await _broadcast(
        "page_navigation",
        {
            "visitor_id": visitor_id,
            "session_id": payload.get("session_id"),
            "page": payload.get("page"),
            "previous_page": payload.get("previous_page"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@sio.event
async def activity(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        activity=data.get("label") or data.get("activity"),
        current_url=data.get("current_url"),
    )
    await _broadcast(
        "activity",
        {
            "visitor_id": visitor_id,
            "session_id": payload.get("session_id"),
            "activity": payload.get("activity"),
            "page": payload.get("page"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@sio.event
async def click(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        activity=f"click:{data.get('selector') or data.get('name') or 'button'}",
        current_url=data.get("current_url"),
    )
    await _broadcast(
        "click",
        {
            "visitor_id": visitor_id,
            "session_id": payload.get("session_id"),
            "selector": data.get("selector") or data.get("name"),
            "page": payload.get("page"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@sio.event
async def session_update(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        page=data.get("page"),
        activity=data.get("activity") or "session_update",
    )
    await _broadcast(
        "session_updated",
        {
            "visitor_id": visitor_id,
            "session_id": payload.get("session_id"),
            "page": payload.get("page"),
            "activity": payload.get("activity"),
            "last_activity": payload.get("last_activity"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@sio.event
async def visitor_location_update(sid: str, data: dict | None = None) -> None:
    if not data:
        return
    visitor_id = str(data.get("visitor_id") or VISITOR_SOCKET_INDEX.get(sid) or uuid.uuid4())
    payload = upsert_active_visitor(
        visitor_id=visitor_id,
        session_id=data.get("session_id"),
        country=data.get("country"),
        city=data.get("city"),
        ip_address=data.get("ip_address"),
        referrer=data.get("referrer"),
        activity="location_update",
    )
    await _broadcast(
        "visitor_location_updated",
        {
            "visitor_id": visitor_id,
            "session_id": payload.get("session_id"),
            "country": payload.get("country"),
            "city": payload.get("city"),
            "ip_address": payload.get("ip_address"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def emit_visitor_presence_update(visitor_id: str, *, payload: dict[str, Any]) -> None:
    await _broadcast("visitor_connected", {"visitor_id": visitor_id, **payload}, rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM])


__all__ = [
    "ACTIVE_VISITORS",
    "REALTIME_EVENTS",
    "sio",
    "connect",
    "disconnect",
    "join_analytics",
    "leave_analytics",
    "visitor_identify",
    "page_view",
    "page_navigation",
    "activity",
    "click",
    "session_update",
    "visitor_location_update",
    "emit_visitor_presence_update",
]
