"""Socket broadcast helpers — analytics, leads, enquiries, notifications.

CRITICAL: This file must NOT define any @sio.event handlers.
All socket event handlers live exclusively in app/realtime/socket_manager.py.
Previously, having @sio.event in both files caused handler-overwrite bugs
because importing socket_service (e.g. via tracking_service) re-registered
connect/disconnect, silently replacing the socket_manager handlers.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.account import Account
from app.realtime.constants import ANALYTICS_REALTIME_ROOM, ADMIN_REALTIME_ROOM
from app.realtime.presence import ACTIVE_VISITORS, get_live_counts, upsert_active_visitor
from app.realtime.socket_manager import sio
from app.utils.cdn_urls import cdn_url_for_value

logger = logging.getLogger(__name__)


def _safe_broadcast(
    event_names: list[str],
    payload: dict[str, Any],
    rooms: list[str],
) -> None:
    """Fire-and-forget broadcast to multiple rooms.
    Safe to call from sync code — schedules a task if a loop is running,
    otherwise uses asyncio.run().
    """
    target_rooms = rooms
    if ADMIN_REALTIME_ROOM in rooms and ANALYTICS_REALTIME_ROOM in rooms:
        target_rooms = [room for room in rooms if room != ANALYTICS_REALTIME_ROOM]

    async def _emit() -> None:
        for room in target_rooms:
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


def _actor_key(actor_type: str, actor_id: uuid.UUID) -> str:
    return f"{actor_type}:{actor_id}"


# ── Lead Broadcasts ────────────────────────────────────────────────────

def emit_lead_created(lead: Any) -> None:
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "lead_score": lead.lead_score,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        "enquiry_id": str(lead.enquiry_id) if lead.enquiry_id else None,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }
    _safe_broadcast(["lead:created", "lead.created"], payload, rooms=[ADMIN_REALTIME_ROOM])


def emit_lead_score_updated(
    lead: Any,
    *,
    previous_score: int,
    new_score: int,
    delta: int,
    reason: str,
) -> None:
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "previous_score": previous_score,
        "new_score": new_score,
        "delta": delta,
        "reason": reason,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
    }
    _safe_broadcast(
        ["lead:score_updated", "lead.score_updated", "lead_score.updated"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


def emit_lead_status_updated(
    lead: Any,
    *,
    previous_status: str,
    new_status: str,
) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


def emit_lead_activity_created(lead: Any, activity: Any) -> None:
    payload = {
        "lead_id": str(lead.id),
        "lead_code": lead.lead_code,
        "activity_id": str(activity.id),
        "activity_type": activity.activity_type,
        "channel": activity.channel.value if hasattr(activity.channel, "value") else str(activity.channel),
        "notes": activity.notes,
        "user_id": str(activity.account_id) if activity.account_id else None,
        "next_follow_up_at": activity.next_follow_up_at.isoformat() if activity.next_follow_up_at else None,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }
    _safe_broadcast(
        ["lead:activity_created", "lead.activity_created"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, f"lead:{lead.id}", f"sales:lead:{lead.id}"],
    )


# ── Enquiry Broadcasts ────────────────────────────────────────────────

def emit_enquiry_created(enquiry: Any) -> None:
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "enquiry_type": enquiry.enquiry_type.value if hasattr(enquiry.enquiry_type, "value") else str(enquiry.enquiry_type),
        "status": enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status),
        "message": enquiry.message,
        "enquirer_name": enquiry.enquirer_name,
        "enquirer_phone": enquiry.enquirer_phone,
        "customer_id": str(enquiry.customer_id) if enquiry.customer_id else None,
        "visitor_id": str(enquiry.visitor_id) if enquiry.visitor_id else None,
        "package_id": str(enquiry.package_id) if enquiry.package_id else None,
        "created_at": enquiry.created_at.isoformat() if enquiry.created_at else None,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:created", "enquiry.created"], payload, rooms=rooms)


def emit_enquiry_updated(enquiry: Any) -> None:
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "status": enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status),
        "enquiry_type": enquiry.enquiry_type.value if hasattr(enquiry.enquiry_type, "value") else str(enquiry.enquiry_type),
        "message": enquiry.message,
        "updated_at": enquiry.updated_at.isoformat() if hasattr(enquiry, "updated_at") and enquiry.updated_at else None,
    }
    rooms = [ADMIN_REALTIME_ROOM, f"enquiry:{enquiry.id}"]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:updated", "enquiry.updated"], payload, rooms=rooms)


def emit_enquiry_status_updated(
    enquiry: Any,
    *,
    previous_status: str,
    new_status: str,
) -> None:
    payload = {
        "enquiry_id": str(enquiry.id),
        "enquiry_code": enquiry.enquiry_code,
        "previous_status": previous_status,
        "new_status": new_status,
    }
    rooms = [ADMIN_REALTIME_ROOM, f"enquiry:{enquiry.id}"]
    if enquiry.customer_id:
        rooms.append(f"CUSTOMER:{enquiry.customer_id}")
    _safe_broadcast(["enquiry:status_updated", "enquiry.status_updated"], payload, rooms=rooms)


# ── Notification Broadcasts ────────────────────────────────────────────

def emit_notification_read(
    *,
    actor_type: str,
    actor_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> None:
    payload = {"notification_id": str(notification_id), "is_read": True}
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
    payload = {"count": count, "unread_count": 0}
    _safe_broadcast(
        ["notification:read_all", "notification.read_all"],
        payload,
        rooms=[_actor_key(actor_type, actor_id)],
    )


# ── Visitor Analytics Broadcasts ──────────────────────────────────────

def emit_visitor_identified(visitor: Any, *, is_new: bool) -> None:
    customer = visitor.customer if visitor.customer_id else None
    if customer is not None and getattr(customer.role, "value", customer.role) != "CUSTOMER":
        customer = None
    visitor_id = str(visitor.id)
    payload = {
        "visitor_id": visitor_id,
        "visitor_code": visitor.visitor_code,
        "fingerprint": visitor.fingerprint,
        "ip_address": visitor.ip_address,
        "country": visitor.country,
        "state": visitor.state,
        "city": visitor.city,
        "browser": visitor.browser,
        "os": visitor.os,
        "device": visitor.device,
        "customer_id": str(visitor.customer_id) if visitor.customer_id else None,
        "customer_name": customer.name if customer else None,
        "customer_email": customer.email if customer else None,
        "customer_mobile": customer.mobile if customer else None,
        "customer_profile_pic": (
            cdn_url_for_value(customer.profile_pic)
            if customer and customer.profile_pic
            else None
        ),
        "is_new": is_new,
        "first_seen": visitor.first_seen.isoformat() if visitor.first_seen else None,
    }
    _safe_broadcast(
        ["analytics:visitor_identified", "analytics.visitor_identified"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM],
    )

    if visitor_id not in ACTIVE_VISITORS:
        return

    upsert_active_visitor(
        visitor_id=visitor_id,
        customer_id=str(visitor.customer_id) if customer else None,
        visitor_type="customer" if customer else "visitor",
        visitor_code=visitor.visitor_code,
        customer_name=customer.name if customer else None,
        customer_email=customer.email if customer else None,
        customer_mobile=customer.mobile if customer else None,
        customer_profile_pic=(
            cdn_url_for_value(customer.profile_pic)
            if customer and customer.profile_pic
            else None
        ),
        is_anonymous=customer is None,
        ip_address=visitor.ip_address,
        country=visitor.country,
        state=visitor.state,
        city=visitor.city,
        device=visitor.device,
        browser=visitor.browser,
        os=visitor.os,
    )
    _safe_broadcast(
        ["visitor_identified"],
        dict(ACTIVE_VISITORS[visitor_id]),
        rooms=[ADMIN_REALTIME_ROOM],
    )
    _safe_broadcast(
        ["live_stats"],
        {**get_live_counts(), "timestamp": datetime.now(timezone.utc).isoformat()},
        rooms=[ADMIN_REALTIME_ROOM],
    )


def emit_session_started(session: Any) -> None:
    payload = {
        "session_id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "landing_page": session.landing_page,
        "referrer": session.referrer,
        "utm_source": session.utm_source,
        "utm_medium": session.utm_medium,
        "utm_campaign": session.utm_campaign,
        "utm_term": session.utm_term,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }
    _safe_broadcast(
        ["analytics:session_started", "analytics.session_started"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM],
    )


def emit_session_heartbeat(session: Any) -> None:
    payload = {
        "session_id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "exit_page": session.exit_page,
        "page_views": session.page_views,
        "duration_seconds": session.duration_seconds,
    }
    _safe_broadcast(
        ["analytics:session_heartbeat", "analytics.session_heartbeat"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM],
    )


def emit_session_ended(session: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM],
    )


def emit_visitor_event(event: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, ANALYTICS_REALTIME_ROOM],
    )


# ── Tour Catalog Broadcasts ───────────────────────────────────────────

def emit_tour_package_created(package: Any) -> None:
    payload = {
        "package_id": str(package.id),
        "tour_code": package.tour_code,
        "slug": package.slug,
        "title": package.title,
        "destination": package.destination,
        "is_active": package.is_active,
        "is_featured": package.is_featured,
    }
    _safe_broadcast(["tour:package_created", "tour.package_created"], payload, rooms=[ADMIN_REALTIME_ROOM])


def emit_tour_package_updated(package: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, f"package:{package.id}"],
    )


def emit_tour_package_deleted(package_id: uuid.UUID) -> None:
    payload = {"package_id": str(package_id)}
    _safe_broadcast(
        ["tour:package_deleted", "tour.package_deleted"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, f"package:{package_id}"],
    )


def emit_tour_variant_created(variant: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, f"package:{variant.package_id}"],
    )


def emit_tour_variant_updated(variant: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, f"package:{variant.package_id}"],
    )


def emit_tour_variant_deleted(variant_id: uuid.UUID, package_id: uuid.UUID) -> None:
    payload = {"variant_id": str(variant_id), "package_id": str(package_id)}
    _safe_broadcast(
        ["tour:variant_deleted", "tour.variant_deleted"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, f"package:{package_id}"],
    )


def emit_tour_detail_updated(detail: Any, package_id: uuid.UUID | None = None) -> None:
    payload = {
        "detail_id": str(detail.id),
        "variant_id": str(detail.variant_id),
        "package_id": str(package_id) if package_id else None,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if package_id:
        rooms.append(f"package:{package_id}")
    _safe_broadcast(["tour:detail_updated", "tour.detail_updated"], payload, rooms=rooms)


# ── Document Broadcasts ───────────────────────────────────────────────

def emit_document_uploaded(document: Any) -> None:
    payload = {
        "document_id": str(document.id),
        "document_type": document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type),
        "title": document.title,
        "customer_id": str(document.customer_id) if document.customer_id else None,
        "file_name": document.file_name,
        "uploaded_by": "CUSTOMER" if document.uploaded_by_account and document.uploaded_by_account.role.value == "CUSTOMER" else "ADMIN",
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if document.customer_id:
        rooms.append(f"CUSTOMER:{document.customer_id}")
    _safe_broadcast(["document:uploaded", "document.uploaded"], payload, rooms=rooms)


def emit_document_deleted(
    document_ids: list[uuid.UUID],
    customer_id: uuid.UUID | None = None,
) -> None:
    payload = {
        "document_ids": [str(d) for d in document_ids],
        "customer_id": str(customer_id) if customer_id else None,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if customer_id:
        rooms.append(f"CUSTOMER:{customer_id}")
    _safe_broadcast(["document:deleted", "document.deleted"], payload, rooms=rooms)


# ── Review Broadcasts ─────────────────────────────────────────────────

def emit_review_created(review: Any) -> None:
    payload = {
        "review_id": str(review.id),
        "package_id": str(review.package_id),
        "customer_id": str(review.customer_id) if review.customer_id else None,
        "rating": review.rating,
        "is_published": review.is_published,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if review.package_id:
        rooms.append(f"package:{review.package_id}")
    _safe_broadcast(["review:created", "review.created"], payload, rooms=rooms)


def emit_review_updated(review: Any) -> None:
    payload = {
        "review_id": str(review.id),
        "package_id": str(review.package_id),
        "customer_id": str(review.customer_id) if review.customer_id else None,
        "rating": review.rating,
    }
    rooms = [ADMIN_REALTIME_ROOM]
    if review.package_id:
        rooms.append(f"package:{review.package_id}")
    _safe_broadcast(["review:updated", "review.updated"], payload, rooms=rooms)


def emit_review_deleted(review_id: uuid.UUID, package_id: uuid.UUID) -> None:
    payload = {"review_id": str(review_id), "package_id": str(package_id)}
    _safe_broadcast(
        ["review:deleted", "review.deleted"],
        payload,
        rooms=[ADMIN_REALTIME_ROOM, f"package:{package_id}"],
    )


# ── Wishlist Broadcasts ───────────────────────────────────────────────

def emit_wishlist_updated(
    customer_id: uuid.UUID,
    *,
    package_id: uuid.UUID,
    action: str,
) -> None:
    payload = {
        "customer_id": str(customer_id),
        "package_id": str(package_id),
        "action": action,
    }
    _safe_broadcast(
        ["wishlist:updated", "wishlist.updated"],
        payload,
        rooms=[f"CUSTOMER:{customer_id}"],
    )


# ── Customer Broadcasts ───────────────────────────────────────────────

def emit_customer_created(customer: Any) -> None:
    payload = {
        "customer_id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "mobile": customer.mobile,
    }
    _safe_broadcast(["customer:created", "customer.created"], payload, rooms=[ADMIN_REALTIME_ROOM])


def emit_customer_updated(customer: Any) -> None:
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
        rooms=[ADMIN_REALTIME_ROOM, f"CUSTOMER:{customer.id}"],
    )


def emit_customer_deleted(customer_id: uuid.UUID) -> None:
    payload = {"customer_id": str(customer_id)}
    _safe_broadcast(["customer:deleted", "customer.deleted"], payload, rooms=[ADMIN_REALTIME_ROOM])


# ── Auth Session Broadcasts ───────────────────────────────────────────

def emit_session_revoked(
    *,
    actor_type: str,
    actor_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
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


# ── Notification publish helper ───────────────────────────────────────

async def publish_notification(item: Any, db: Any | None = None) -> None:
    recipients = getattr(item, "recipient_ids", None) or []
    if not recipients:
        single = (
            getattr(item, "customer_id", None)
            or getattr(item, "user_id", None)
            or getattr(item, "recipient_id", None)
        )
        if single:
            recipients = [single]
    if not recipients:
        return

    session = db
    close_session = False
    if session is None:
        try:
            session = SessionLocal()
            close_session = True
        except Exception:
            session = None

    try:
        for rec_id in recipients:
            actor_type = "CUSTOMER"
            if session is not None:
                try:
                    role = session.scalar(select(Account.role).where(Account.id == rec_id))
                    role_val = getattr(role, "value", str(role)).upper() if role else "CUSTOMER"
                    actor_type = "CUSTOMER" if role_val == "CUSTOMER" else "ADMIN"
                except Exception:
                    pass

            await sio.emit(
                "notification.created",
                {
                    "id": str(item.id),
                    "notification_type": item.notification_type,
                    "title": item.title,
                    "message": item.message,
                    "data": item.data,
                    "is_read": getattr(item, "is_read", False),
                    "read_at": item.read_at.isoformat() if getattr(item, "read_at", None) else None,
                    "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
                },
                room=_actor_key(actor_type, rec_id),
            )
    finally:
        if close_session and session is not None:
            session.close()
