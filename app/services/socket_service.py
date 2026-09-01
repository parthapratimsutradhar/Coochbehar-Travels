import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

import socketio
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.user import User
from app.models.visitor import Visitor
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

_connections: dict[str, set[str]] = defaultdict(set)
_sessions: dict[str, tuple[str, uuid.UUID]] = {}


def _actor_key(actor_type: str, actor_id: uuid.UUID) -> str:
    return f"{actor_type}:{actor_id}"


def _safe_broadcast(
    event_names: list[str],
    payload: dict[str, Any],
    rooms: list[str],
) -> None:
    """Helper to broadcast events across multiple rooms asynchronously."""

    async def _emit() -> None:
        for room in rooms:
            for event_name in event_names:
                try:
                    await sio.emit(event_name, payload, room=room)
                except Exception:
                    logger.exception("Failed to emit %s to room %s", event_name, room)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.run(_emit())
        except Exception:
            logger.exception("Failed to run async broadcast for %s", event_names)
    else:
        try:
            loop.create_task(_emit())
        except Exception:
            logger.exception("Failed to schedule broadcast task for %s", event_names)


# ── Real-Time Sales Lead Broadcasts ───────────────────────────────────

def emit_lead_created(lead: Lead) -> None:
    """Emit lead:created event to admin sockets upon committed lead creation."""
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "lead_score": lead.lead_score,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        "source": lead.source.value if hasattr(lead.source, "value") else str(lead.source),
        "full_name": lead.full_name,
        "mobile": lead.mobile,
        "email": lead.email,
        "enquiry_id": str(lead.enquiry_id) if lead.enquiry_id else None,
        "customer_id": str(lead.customer_id) if lead.customer_id else None,
        "visitor_id": str(lead.visitor_id) if lead.visitor_id else None,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }
    _safe_broadcast(["lead:created", "lead.created"], payload, rooms=["ADMIN"])


def emit_lead_score_updated(
    lead: Lead,
    *,
    previous_score: int,
    new_score: int,
    delta: int,
    reason: str,
) -> None:
    """Emit lead:score_updated to admin sockets and lead-specific room."""
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "previous_score": previous_score,
        "new_score": new_score,
        "delta": delta,
        "reason": reason,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        "customer_id": str(lead.customer_id) if lead.customer_id else None,
        "visitor_id": str(lead.visitor_id) if lead.visitor_id else None,
    }
    _safe_broadcast(
        ["lead:score_updated", "lead.score_updated", "lead_score.updated"],
        payload,
        rooms=["ADMIN", f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


def emit_lead_status_updated(
    lead: Lead,
    *,
    previous_status: str,
    new_status: str,
) -> None:
    """Emit lead:status_updated to admin sockets and lead-specific room."""
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "previous_status": previous_status,
        "new_status": new_status,
        "lead_score": lead.lead_score,
    }
    _safe_broadcast(
        ["lead:status_updated", "lead.status_updated"],
        payload,
        rooms=["ADMIN", f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


def emit_lead_activity_created(
    lead: Lead,
    activity: LeadActivity,
) -> None:
    """Emit lead:activity_created to admin sockets upon logging activity."""
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "activity_id": str(activity.id),
        "activity_type": activity.activity_type,
        "channel": activity.channel.value if hasattr(activity.channel, "value") else str(activity.channel),
        "notes": activity.notes,
        "user_id": str(activity.user_id) if activity.user_id else None,
        "next_follow_up_at": activity.next_follow_up_at.isoformat() if activity.next_follow_up_at else None,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }
    _safe_broadcast(
        ["lead:activity_created", "lead.activity_created"],
        payload,
        rooms=["ADMIN", f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


# ── Socket Lifecycle & Events ─────────────────────────────────────────

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
async def join_lead(sid: str, data: dict | None = None) -> None:
    """Allow connected staff/admin to subscribe to updates for a specific lead."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    lead_id = data.get("lead_id")
    if lead_id:
        await sio.enter_room(sid, f"lead:{lead_id}")
        await sio.enter_room(sid, f"sales:lead:{lead_id}")


@sio.event
async def leave_lead(sid: str, data: dict | None = None) -> None:
    """Unsubscribe from updates for a specific lead."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    lead_id = data.get("lead_id")
    if lead_id:
        await sio.leave_room(sid, f"lead:{lead_id}")
        await sio.leave_room(sid, f"sales:lead:{lead_id}")


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
            from app.services.tracking_service import TrackingService

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
