"""Lead scoring service — centralized dynamic scoring for sales leads.

Responsibilities:
- Calculate initial score from an enquiry.
- Calculate event score delta from meaningful visitor telemetry actions.
- Prevent score farming and apply rate-limiting / deduplication / daily caps.
- Calculate activity score delta from staff sales activities.
- Apply bounded score updates (0 <= lead_score <= 100).
- Find and associate leads with visitors/customers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.visitor_event import VisitorEvent

logger = logging.getLogger(__name__)

# ── Event Delta Configuration ─────────────────────────────────────────
MEANINGFUL_EVENT_SCORES: dict[str, int] = {
    # Tour package & content interest
    "tour_package_view": 5,
    "tour_variant_view": 5,
    "itinerary_view": 4,
    "gallery_view": 3,
    "review_read": 3,
    "compare_packages": 5,
    "wishlist_add": 10,
    "tour_wishlist_add": 10,
    "add_to_wishlist": 10,
    
    # High-intent actions
    "price_check": 8,
    "price_view": 8,
    "date_check": 5,
    "whatsapp_click": 8,
    "phone_click": 8,
    "enquiry_form_open": 5,
    "enquiry_form_fill": 8,
    "enquiry_started": 5,
    "quote_view": 8,
    "booking_page_view": 8,
    
    # Conversion events (if tracked via telemetry)
    "enquiry_submit": 25,
    "booking_enquiry": 25,
    "custom_tour_request": 25,
}

# Events that should NOT generate lead score points (noise/telemetry only)
NON_SCORING_EVENTS: set[str] = {
    "heartbeat",
    "page_leave",
    "session_start",
    "session_end",
    "session_update",
    "scroll_depth_50",
    "scroll_depth_75",
    "scroll_depth_100",
    "time_on_page_30s",
    "time_on_page_60s",
    "video_play",
    "login",
    "signup",
    "google_oauth",
}

# ── Staff Activity Score Configuration ────────────────────────────────
ACTIVITY_SCORES: dict[str, int] = {
    "CALL": 5,
    "WHATSAPP": 5,
    "EMAIL": 3,
    "FOLLOW_UP": 4,
    "QUOTE_SENT": 10,
    "CUSTOMER_RESPONDED": 10,
    "DOCUMENT_REQUESTED": 5,
    "DOCUMENT_RECEIVED": 10,
    "INTEREST_CONFIRMED": 15,
}
DEFAULT_ACTIVITY_SCORE: int = 2

# Maximum score increments from repetitive event types per day
EVENT_DAILY_CAP: dict[str, int] = {
    "tour_package_view": 15,
    "tour_variant_view": 15,
    "itinerary_view": 12,
    "price_check": 16,
    "whatsapp_click": 16,
    "phone_click": 16,
    "enquiry_form_open": 10,
    "enquiry_form_fill": 16,
}
DEFAULT_DAILY_CAP: int = 20


class LeadScoringService:
    """Centralized sales lead scoring engine."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Initial Scoring for Enquiries ─────────────────────────────────

    def calculate_initial_score(self, enquiry: Enquiry | dict[str, Any]) -> int:
        """Compute the initial lead score from enquiry attributes.

        Scoring Rules:
        - Base submission: +20
        - Travel date provided: +10
        - Destination provided: +5
        - Pax count provided: +5
        - Specific package/variant selected: +10
        - Enquirer phone provided: +10
        - Enquirer name provided: +5
        - Special requirements/message provided: +5

        Strictly bounded: 0 <= score <= 100.
        """
        score = 20  # Base submission

        if isinstance(enquiry, Enquiry):
            travel_date = enquiry.travel_date
            destination = enquiry.destination
            pax_no = enquiry.pax_no
            package_id = enquiry.package_id
            variant_id = enquiry.variant_id
            phone = enquiry.enquirer_phone
            name = enquiry.enquirer_name
            message = enquiry.message or enquiry.special_requirements
        else:
            travel_date = enquiry.get("travel_date")
            destination = enquiry.get("destination")
            pax_no = enquiry.get("pax_no")
            package_id = enquiry.get("package_id")
            variant_id = enquiry.get("variant_id")
            phone = enquiry.get("enquirer_phone") or enquiry.get("mobile")
            name = enquiry.get("enquirer_name") or enquiry.get("name")
            message = enquiry.get("message") or enquiry.get("special_requirements")

        if travel_date:
            score += 10
        if destination and str(destination).strip():
            score += 5
        if pax_no is not None and pax_no > 0:
            score += 5
        if package_id or variant_id:
            score += 10
        if phone and str(phone).strip():
            score += 10
        if name and str(name).strip():
            score += 5
        if message and str(message).strip():
            score += 5

        return max(0, min(100, score))

    # ── Event Delta Scoring ───────────────────────────────────────────

    def calculate_event_score(
        self,
        event_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Resolve the raw score delta for a visitor telemetry event."""
        norm_name = event_name.lower().strip()
        if norm_name in NON_SCORING_EVENTS:
            return 0

        delta = MEANINGFUL_EVENT_SCORES.get(norm_name, 0)
        if delta == 0:
            # Default fallback for unlisted page views / noise
            return 0

        # Wishlist bonus boost if metadata indicates package was saved
        if isinstance(metadata, dict):
            if metadata.get("is_wishlist") is True or metadata.get("package_wishlisted") is True:
                delta += 5

        return delta

    # ── Anti-Farming & Deduplication ──────────────────────────────────

    def is_event_farmed(
        self,
        visitor_id: uuid.UUID,
        event_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Check if an event is duplicate / farmed to prevent score inflation.

        Rules:
        1. Duplicate resource interaction (e.g. repeated package view on same package)
           within the last 15 minutes is ignored.
        2. Rapid repeated click/event of the exact same event type within 2 minutes is ignored.
        3. Daily event frequency cap per event type is enforced.
        """
        norm_name = event_name.lower().strip()
        now = datetime.now(timezone.utc)

        # Check 1: Rapid duplicate event within 2 minutes
        short_window = now - timedelta(minutes=2)
        recent_same_event_count = self.db.execute(
            select(func.count(VisitorEvent.id)).where(
                VisitorEvent.visitor_id == visitor_id,
                VisitorEvent.event_name == event_name,
                VisitorEvent.created_at >= short_window,
            )
        ).scalar_one() or 0

        if recent_same_event_count > 1:
            return True

        # Check 2: Same package/resource view within 15 minutes
        if isinstance(metadata, dict):
            resource_id = metadata.get("package_id") or metadata.get("slug") or metadata.get("url")
            if resource_id:
                resource_window = now - timedelta(minutes=15)
                # Count recent events with matching resource in metadata
                recent_events = self.db.execute(
                    select(VisitorEvent).where(
                        VisitorEvent.visitor_id == visitor_id,
                        VisitorEvent.event_name == event_name,
                        VisitorEvent.created_at >= resource_window,
                    )
                ).scalars().all()

                matching = 0
                for ev in recent_events:
                    if isinstance(ev.event_metadata, dict):
                        ev_res = (
                            ev.event_metadata.get("package_id")
                            or ev.event_metadata.get("slug")
                            or ev.event_metadata.get("url")
                        )
                        if ev_res == resource_id:
                            matching += 1
                if matching > 1:
                    return True

        # Check 3: Daily cap for this event type
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
        today_events_count = self.db.execute(
            select(func.count(VisitorEvent.id)).where(
                VisitorEvent.visitor_id == visitor_id,
                VisitorEvent.event_name == event_name,
                VisitorEvent.created_at >= today_start,
            )
        ).scalar_one() or 0

        cap = EVENT_DAILY_CAP.get(norm_name, DEFAULT_DAILY_CAP)
        # Assuming each event earns ~5 points, max events = cap / points
        points_per_event = MEANINGFUL_EVENT_SCORES.get(norm_name, 5)
        max_events_today = max(1, cap // max(1, points_per_event))
        if today_events_count > max_events_today:
            return True

        return False

    # ── Activity Scoring ──────────────────────────────────────────────

    def calculate_activity_score(
        self,
        activity: LeadActivity | dict[str, Any],
    ) -> int:
        """Calculate the lead score delta from staff sales activity."""
        if isinstance(activity, LeadActivity):
            act_type = activity.activity_type
        else:
            act_type = activity.get("activity_type", "")

        norm_type = str(act_type).upper().strip()
        return ACTIVITY_SCORES.get(norm_type, DEFAULT_ACTIVITY_SCORE)

    # ── Score Application & Lead Lookup ───────────────────────────────

    def apply_score_change(
        self,
        lead: Lead,
        delta: int,
        reason: str = "activity",
    ) -> tuple[int, int, int]:
        """Apply a score delta to a Lead, guaranteeing 0 <= score <= 100.

        Returns (previous_score, new_score, actual_delta).
        """
        prev_score = lead.lead_score
        new_score = max(0, min(100, prev_score + delta))
        actual_delta = new_score - prev_score
        lead.lead_score = new_score
        return prev_score, new_score, actual_delta

    def find_lead_for_visitor(
        self,
        visitor_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> Lead | None:
        """Find the active sales Lead corresponding to a visitor or customer.

        Follows the canonical Enquiry -> Lead relationship.
        """
        if not visitor_id and not customer_id:
            return None

        # 1. Direct query on Lead table (newest lead first)
        stmt = select(Lead)
        if visitor_id and customer_id:
            stmt = stmt.where((Lead.visitor_id == visitor_id) | (Lead.customer_id == customer_id))
        elif visitor_id:
            stmt = stmt.where(Lead.visitor_id == visitor_id)
        elif customer_id:
            stmt = stmt.where(Lead.customer_id == customer_id)

        stmt = stmt.order_by(Lead.created_at.desc())
        lead = self.db.execute(stmt).scalars().first()
        if lead:
            return lead

        # 2. Lookup through Enquiry table if not linked directly on Lead
        enq_stmt = select(Enquiry)
        if visitor_id and customer_id:
            enq_stmt = enq_stmt.where((Enquiry.visitor_id == visitor_id) | (Enquiry.customer_id == customer_id))
        elif visitor_id:
            enq_stmt = enq_stmt.where(Enquiry.visitor_id == visitor_id)
        elif customer_id:
            enq_stmt = enq_stmt.where(Enquiry.customer_id == customer_id)

        enq_stmt = enq_stmt.order_by(Enquiry.created_at.desc())
        enquiry = self.db.execute(enq_stmt).scalars().first()
        if enquiry and enquiry.lead:
            return enquiry.lead

        return None

    def recalculate_score(self, lead: Lead) -> int:
        """Recalculate lead score from scratch based on enquiry, events, and activities."""
        base_score = 0
        if lead.enquiry:
            base_score = self.calculate_initial_score(lead.enquiry)
        elif lead.notes:
            base_score = 20

        # Add activity scores
        activity_total = 0
        if lead.activities:
            for act in lead.activities:
                activity_total += self.calculate_activity_score(act)

        total = max(0, min(100, base_score + activity_total))
        lead.lead_score = total
        return total
