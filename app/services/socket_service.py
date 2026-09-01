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


# ── Enquiry Broadcasts ────────────────────────────────────────────────

def emit_enquiry_created(enquiry: Any) -> None:
    """Emit enquiry:created when a new enquiry is submitted by enduser."""
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "enquiry_type": enquiry.enquiry_type.value if hasattr(enquiry.enquiry_type, "value") else str(enquiry.enquiry_type),
        "status": enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status),
        "subject": enquiry.subject,
        "enquirer_name": enquiry.enquirer_name,
        "enquirer_phone": enquiry.enquirer_phone,
        "customer_id": str(enquiry.customer_id) if enquiry.customer_id else None,
        "visitor_id": str(enquiry.visitor_id) if enquiry.visitor_id else None,
        "package_id": str(enquiry.package_id) if enquiry.package_id else None,
        "created_at": enquiry.created_at.isoformat() if enquiry.created_at else None,
    }
    rooms = ["ADMIN"]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:created", "enquiry.created"], payload, rooms=rooms)


def emit_enquiry_updated(enquiry: Any) -> None:
    """Emit enquiry:updated when admin updates enquiry fields."""
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "status": enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status),
        "enquiry_type": enquiry.enquiry_type.value if hasattr(enquiry.enquiry_type, "value") else str(enquiry.enquiry_type),
        "subject": enquiry.subject,
        "updated_at": enquiry.updated_at.isoformat() if hasattr(enquiry, "updated_at") and enquiry.updated_at else None,
    }
    rooms = ["ADMIN", f"enquiry:{enquiry.id}"]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:updated", "enquiry.updated"], payload, rooms=rooms)


def emit_enquiry_status_updated(
    enquiry: Any,
    *,
    previous_status: str,
    new_status: str,
) -> None:
    """Emit enquiry:status_updated with before/after state."""
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "previous_status": previous_status,
        "new_status": new_status,
    }
    rooms = ["ADMIN", f"enquiry:{enquiry.id}"]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:status_updated", "enquiry.status_updated"], payload, rooms=rooms)


# ── Notification Broadcasts ───────────────────────────────────────────

def emit_notification_read(
    *,
    actor_type: str,
    actor_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> None:
    """Emit notification:read to sync read-state across devices/tabs."""
    payload = {
        "notification_id": str(notification_id),
        "is_read": True,
    }
    _safe_broadcast(
        ["notification:read", "notification.read"],
        payload,
        rooms=[_actor_key(actor_type, actor_id)],
    )


def emit_notification_read_all(
    *,
    actor_type: str,
    actor_id: uuid.UUID,
    count: int,
) -> None:
    """Emit notification:read_all when bulk-marking notifications as read."""
    payload = {
        "count": count,
        "unread_count": 0,
    }
    _safe_broadcast(
        ["notification:read_all", "notification.read_all"],
        payload,
        rooms=[_actor_key(actor_type, actor_id)],
    )


# ── Visitor Analytics Broadcasts ──────────────────────────────────────

def emit_visitor_identified(visitor: Any, *, is_new: bool) -> None:
    """Emit analytics:visitor_identified to live admin analytics dashboard."""
    payload = {
        "visitor_id": str(visitor.id),
        "fingerprint": visitor.fingerprint,
        "ip_address": visitor.ip_address,
        "country": visitor.country,
        "city": visitor.city,
        "browser": visitor.browser,
        "os": visitor.os,
        "device": visitor.device,
        "is_new": is_new,
        "first_seen": visitor.first_seen.isoformat() if visitor.first_seen else None,
    }
    _safe_broadcast(
        ["analytics:visitor_identified", "analytics.visitor_identified"],
        payload,
        rooms=["ADMIN", "analytics:live"],
    )


def emit_session_started(session: Any) -> None:
    """Emit analytics:session_started when a new visitor session begins."""
    payload = {
        "session_id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "landing_page": session.landing_page,
        "referrer": session.referrer,
        "utm_source": session.utm_source,
        "utm_medium": session.utm_medium,
        "utm_campaign": session.utm_campaign,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }
    _safe_broadcast(
        ["analytics:session_started", "analytics.session_started"],
        payload,
        rooms=["ADMIN", "analytics:live"],
    )


def emit_session_heartbeat(session: Any) -> None:
    """Emit analytics:session_heartbeat with current page and page view delta."""
    payload = {
        "session_id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "exit_page": session.exit_page,
        "page_views": session.page_views,
    }
    _safe_broadcast(
        ["analytics:session_heartbeat", "analytics.session_heartbeat"],
        payload,
        rooms=["ADMIN", "analytics:live"],
    )


def emit_session_ended(session: Any) -> None:
    """Emit analytics:session_ended when a visitor session is finalised."""
    payload = {
        "session_id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "exit_page": session.exit_page,
        "duration_seconds": session.duration_seconds,
        "page_views": session.page_views,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
    _safe_broadcast(
        ["analytics:session_ended", "analytics.session_ended"],
        payload,
        rooms=["ADMIN", "analytics:live"],
    )


def emit_visitor_event(event: Any) -> None:
    """Emit analytics:visitor_event for each tracked visitor interaction."""
    payload = {
        "event_id": str(event.id),
        "visitor_id": str(event.visitor_id),
        "session_id": str(event.session_id),
        "event_name": event.event_name,
        "page": event.page,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    _safe_broadcast(
        ["analytics:visitor_event", "analytics.visitor_event"],
        payload,
        rooms=["ADMIN", "analytics:live"],
    )


# ── Tour Catalog Broadcasts ──────────────────────────────────────────

def emit_tour_package_created(package: Any) -> None:
    """Emit tour:package_created to admin and enduser consumers."""
    payload = {
        "package_id": str(package.id),
        "tour_code": package.tour_code,
        "slug": package.slug,
        "title": package.title,
        "destination": package.destination,
        "is_active": package.is_active,
        "is_featured": package.is_featured,
    }
    _safe_broadcast(["tour:package_created", "tour.package_created"], payload, rooms=["ADMIN"])


def emit_tour_package_updated(package: Any) -> None:
    """Emit tour:package_updated for live catalog sync."""
    payload = {
        "package_id": str(package.id),
        "tour_code": package.tour_code,
        "slug": package.slug,
        "title": package.title,
        "destination": package.destination,
        "is_active": package.is_active,
        "is_featured": package.is_featured,
    }
    _safe_broadcast(
        ["tour:package_updated", "tour.package_updated"],
        payload,
        rooms=["ADMIN", f"package:{package.id}"],
    )


def emit_tour_package_deleted(package_id: uuid.UUID) -> None:
    """Emit tour:package_deleted when a tour package is removed."""
    payload = {"package_id": str(package_id)}
    _safe_broadcast(
        ["tour:package_deleted", "tour.package_deleted"],
        payload,
        rooms=["ADMIN", f"package:{package_id}"],
    )


def emit_tour_variant_created(variant: Any) -> None:
    """Emit tour:variant_created for variant management live sync."""
    payload = {
        "variant_id": str(variant.id),
        "package_id": str(variant.package_id),
        "slug": variant.slug,
        "name": variant.name,
        "season_name": variant.season_name,
        "is_active": variant.is_active,
    }
    _safe_broadcast(
        ["tour:variant_created", "tour.variant_created"],
        payload,
        rooms=["ADMIN", f"package:{variant.package_id}"],
    )


def emit_tour_variant_updated(variant: Any) -> None:
    """Emit tour:variant_updated when variant details change."""
    payload = {
        "variant_id": str(variant.id),
        "package_id": str(variant.package_id),
        "slug": variant.slug,
        "name": variant.name,
        "season_name": variant.season_name,
        "is_active": variant.is_active,
    }
    _safe_broadcast(
        ["tour:variant_updated", "tour.variant_updated"],
        payload,
        rooms=["ADMIN", f"package:{variant.package_id}"],
    )


def emit_tour_variant_deleted(variant_id: uuid.UUID, package_id: uuid.UUID) -> None:
    """Emit tour:variant_deleted on variant removal."""
    payload = {
        "variant_id": str(variant_id),
        "package_id": str(package_id),
    }
    _safe_broadcast(
        ["tour:variant_deleted", "tour.variant_deleted"],
        payload,
        rooms=["ADMIN", f"package:{package_id}"],
    )


def emit_tour_detail_updated(detail: Any, package_id: uuid.UUID | None = None) -> None:
    """Emit tour:detail_updated when itinerary details are modified."""
    payload = {
        "detail_id": str(detail.id),
        "variant_id": str(detail.variant_id),
        "package_id": str(package_id) if package_id else None,
    }
    rooms = ["ADMIN"]
    if package_id:
        rooms.append(f"package:{package_id}")
    _safe_broadcast(["tour:detail_updated", "tour.detail_updated"], payload, rooms=rooms)


# ── Document Broadcasts ──────────────────────────────────────────────

def emit_document_uploaded(document: Any) -> None:
    """Emit document:uploaded when a document is uploaded by admin or customer."""
    payload = {
        "document_id": str(document.id),
        "document_type": document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type),
        "title": document.title,
        "customer_id": str(document.customer_id) if document.customer_id else None,
        "file_name": document.file_name,
        "uploaded_by": "CUSTOMER" if document.uploaded_by_customer_id else "ADMIN",
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
    }
    rooms = ["ADMIN"]
    if document.customer_id:
        rooms.append(f"CUSTOMER:{document.customer_id}")
    _safe_broadcast(["document:uploaded", "document.uploaded"], payload, rooms=rooms)


def emit_document_deleted(
    document_ids: list[uuid.UUID],
    customer_id: uuid.UUID | None = None,
) -> None:
    """Emit document:deleted when documents are soft-deleted."""
    payload = {
        "document_ids": [str(d) for d in document_ids],
        "customer_id": str(customer_id) if customer_id else None,
    }
    rooms = ["ADMIN"]
    if customer_id:
        rooms.append(f"CUSTOMER:{customer_id}")
    _safe_broadcast(["document:deleted", "document.deleted"], payload, rooms=rooms)


# ── Review Broadcasts ────────────────────────────────────────────────

def emit_review_created(review: Any) -> None:
    """Emit review:created when a customer publishes a new review."""
    payload = {
        "review_id": str(review.id),
        "package_id": str(review.package_id),
        "customer_id": str(review.customer_id) if review.customer_id else None,
        "rating": review.rating,
        "is_published": review.is_published,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
    rooms = ["ADMIN"]
    if review.package_id:
        rooms.append(f"package:{review.package_id}")
    _safe_broadcast(["review:created", "review.created"], payload, rooms=rooms)


def emit_review_updated(review: Any) -> None:
    """Emit review:updated when a customer edits their review."""
    payload = {
        "review_id": str(review.id),
        "package_id": str(review.package_id),
        "customer_id": str(review.customer_id) if review.customer_id else None,
        "rating": review.rating,
    }
    rooms = ["ADMIN"]
    if review.package_id:
        rooms.append(f"package:{review.package_id}")
    _safe_broadcast(["review:updated", "review.updated"], payload, rooms=rooms)


def emit_review_deleted(review_id: uuid.UUID, package_id: uuid.UUID) -> None:
    """Emit review:deleted when a review is soft-deleted."""
    payload = {
        "review_id": str(review_id),
        "package_id": str(package_id),
    }
    _safe_broadcast(
        ["review:deleted", "review.deleted"],
        payload,
        rooms=["ADMIN", f"package:{package_id}"],
    )


# ── Wishlist Broadcasts ──────────────────────────────────────────────

def emit_wishlist_updated(
    customer_id: uuid.UUID,
    *,
    package_id: uuid.UUID,
    action: str,
) -> None:
    """Emit wishlist:updated to sync across customer tabs/devices."""
    payload = {
        "customer_id": str(customer_id),
        "package_id": str(package_id),
        "action": action,  # "added" | "removed"
    }
    _safe_broadcast(
        ["wishlist:updated", "wishlist.updated"],
        payload,
        rooms=[f"CUSTOMER:{customer_id}"],
    )


# ── Customer Broadcasts ──────────────────────────────────────────────

def emit_customer_created(customer: Any) -> None:
    """Emit customer:created to admin dashboard."""
    payload = {
        "customer_id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "mobile": customer.mobile,
    }
    _safe_broadcast(["customer:created", "customer.created"], payload, rooms=["ADMIN"])


def emit_customer_updated(customer: Any) -> None:
    """Emit customer:updated to admin dashboard and customer's own room."""
    payload = {
        "customer_id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "mobile": customer.mobile,
        "is_active": customer.is_active,
    }
    _safe_broadcast(
        ["customer:updated", "customer.updated"],
        payload,
        rooms=["ADMIN", f"CUSTOMER:{customer.id}"],
    )


def emit_customer_deleted(customer_id: uuid.UUID) -> None:
    """Emit customer:deleted to admin dashboard."""
    payload = {"customer_id": str(customer_id)}
    _safe_broadcast(["customer:deleted", "customer.deleted"], payload, rooms=["ADMIN"])


# ── Auth Session Broadcasts ──────────────────────────────────────────

def emit_session_revoked(
    *,
    actor_type: str,
    actor_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    """Emit auth:session_revoked so clients can invalidate tokens."""
    payload = {
        "session_id": str(session_id),
        "actor_type": actor_type,
        "actor_id": str(actor_id),
    }
    _safe_broadcast(
        ["auth:session_revoked", "auth.session_revoked"],
        payload,
        rooms=[_actor_key(actor_type, actor_id)],
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
async def join_enquiry(sid: str, data: dict | None = None) -> None:
    """Subscribe to updates for a specific enquiry."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    enquiry_id = data.get("enquiry_id")
    if enquiry_id:
        await sio.enter_room(sid, f"enquiry:{enquiry_id}")


@sio.event
async def leave_enquiry(sid: str, data: dict | None = None) -> None:
    """Unsubscribe from enquiry updates."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    enquiry_id = data.get("enquiry_id")
    if enquiry_id:
        await sio.leave_room(sid, f"enquiry:{enquiry_id}")


@sio.event
async def join_package(sid: str, data: dict | None = None) -> None:
    """Subscribe to updates for a specific tour package."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    package_id = data.get("package_id")
    if package_id:
        await sio.enter_room(sid, f"package:{package_id}")


@sio.event
async def leave_package(sid: str, data: dict | None = None) -> None:
    """Unsubscribe from tour package updates."""
    session = _sessions.get(sid)
    if not session or not data:
        return
    package_id = data.get("package_id")
    if package_id:
        await sio.leave_room(sid, f"package:{package_id}")


@sio.event
async def join_analytics(sid: str, data: dict | None = None) -> None:
    """Subscribe to live analytics feed (admin only)."""
    session = _sessions.get(sid)
    if not session:
        return
    key, _ = session
    if key.startswith("ADMIN:") or key.startswith("STAFF:"):
        await sio.enter_room(sid, "analytics:live")


@sio.event
async def leave_analytics(sid: str, data: dict | None = None) -> None:
    """Unsubscribe from live analytics feed."""
    session = _sessions.get(sid)
    if not session:
        return
    await sio.leave_room(sid, "analytics:live")


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
