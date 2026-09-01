import uuid
from collections import defaultdict

import socketio
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.customer import Customer
from app.models.user import User
from app.services.tracking_service import TrackingService
from app.utils.security import decode_access_token


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

_connections: dict[str, set[str]] = defaultdict(set)
_sessions: dict[str, tuple[str, uuid.UUID]] = {}


def _actor_key(actor_type: str, actor_id: uuid.UUID) -> str:
    return f"{actor_type}:{actor_id}"


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> bool:
    token = (auth or {}).get("token")
    payload = decode_access_token(token) if token else None
    actor_type = payload.get("role", "").upper() if payload else ""
    subject = payload.get("sub") if payload else None
    if actor_type not in {"CUSTOMER", "ADMIN", "STAFF"} or not subject:
        return False
    try:
        actor_id = uuid.UUID(subject)
    except ValueError:
        return False

    db = SessionLocal()
    try:
        model = Customer if actor_type == "CUSTOMER" else User
        if not db.scalar(select(model.id).where(model.id == actor_id, model.is_active.is_(True))):
            return False
    finally:
        db.close()

    key = _actor_key(actor_type, actor_id)
    _connections[key].add(sid)
    _sessions[sid] = (key, actor_id)
    await sio.save_session(sid, {"actor_type": actor_type, "actor_id": str(actor_id)})
    await sio.enter_room(sid, key)
    if actor_type in {"ADMIN", "STAFF"}:
        await sio.enter_room(sid, "ADMIN")
    await sio.emit(
        "presence.updated",
        {"actor_type": actor_type, "actor_id": str(actor_id), "online": True},
        room="ADMIN",
    )
    return True


@sio.event
async def disconnect(sid: str) -> None:
    session = _sessions.pop(sid, None)
    if not session:
        return
    key, actor_id = session
    sockets = _connections[key]
    sockets.discard(sid)
    if not sockets:
        _connections.pop(key, None)
        actor_type = key.split(":", 1)[0]
        await sio.emit(
            "presence.updated",
            {"actor_type": actor_type, "actor_id": str(actor_id), "online": False},
            room="ADMIN",
        )


@sio.event
async def track_page(sid: str, data: dict | None = None) -> None:
    session = _sessions.get(sid)
    if not session or not data:
        return
    actor_key, actor_id = session
    page = data.get("page")
    visitor_id = data.get("visitor_id")
    session_id = data.get("session_id")
    if not page:
        return

    if visitor_id and session_id:
        db = SessionLocal()
        try:
            TrackingService(db).track_event(
                uuid.UUID(visitor_id),
                uuid.UUID(session_id),
                event_name="page_view",
                page=page,
                metadata={"realtime": True},
            )
        finally:
            db.close()

    await sio.emit(
        "customer.page_view",
        {
            "actor": actor_key,
            "actor_id": str(actor_id),
            "page": page,
            "visitor_id": visitor_id,
            "session_id": session_id,
        },
        room="ADMIN",
    )


async def publish_notification(item) -> None:
    recipient_id = item.customer_id or item.user_id
    if not recipient_id:
        return
    actor_type = "CUSTOMER" if item.customer_id else "ADMIN"
    await sio.emit(
        "notification.created",
        {
            "id": str(item.id),
            "notification_type": item.notification_type,
            "title": item.title,
            "message": item.message,
            "data": item.data,
            "is_read": item.is_read,
            "read_at": item.read_at.isoformat() if item.read_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        },
        room=_actor_key(actor_type, recipient_id),
    )
