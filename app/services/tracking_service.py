"""Tracking service — orchestrates visitor identification, session
lifecycle, event tracking, and sales lead-score integration.

Sits between the API layer and the repository layer, applying
business rules (session auto-events, lead-score propagation) that
don't belong in either.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession
from app.repository.visitor_repo import VisitorRepository
from app.services.lead_scoring_service import LeadScoringService
from app.services.socket_service import emit_lead_score_updated

logger = logging.getLogger(__name__)


class TrackingService:
    """High-level orchestration for the visitor analytics subsystem."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VisitorRepository(db)
        self.scoring_service = LeadScoringService(db)

    # ── Visitor identification ────────────────────────────────────────

    def identify_visitor(
        self,
        *,
        fingerprint: str | None = None,
        ip_address: str | None = None,
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
        browser: str | None = None,
        os: str | None = None,
        device: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[Visitor, bool]:
        """Identify (upsert) a visitor by fingerprint.

        Returns ``(visitor, is_new)``.
        """
        return self.repo.get_or_create(
            fingerprint,
            ip_address=ip_address,
            country=country,
            state=state,
            city=city,
            browser=browser,
            os=os,
            device=device,
            customer_id=customer_id,
        )

    # ── Session lifecycle ─────────────────────────────────────────────

    def start_session(
        self,
        visitor_id: uuid.UUID,
        *,
        landing_page: str | None = None,
        referrer: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_term: str | None = None,
    ) -> VisitorSession:
        """Start a new browsing session and log a ``session_start`` event."""
        session = self.repo.create_session(
            visitor_id,
            landing_page=landing_page,
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_term=utm_term,
        )
        # Log a synthetic session-start event
        self.repo.create_event(
            visitor_id,
            session.id,
            event_name="session_start",
            page=landing_page,
            event_metadata={
                "referrer": referrer,
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
            },
        )
        return session

    def heartbeat(
        self,
        session_id: uuid.UUID,
        *,
        current_page: str | None = None,
        page_views_delta: int = 0,
    ) -> VisitorSession | None:
        """Keep a session alive — update exit page and pageview count."""
        return self.repo.heartbeat_session(
            session_id,
            current_page=current_page,
            page_views_delta=page_views_delta,
        )

    def end_session(
        self,
        session_id: uuid.UUID,
        *,
        exit_page: str | None = None,
    ) -> VisitorSession | None:
        """Finalise a session and log a ``session_end`` event."""
        session = self.repo.end_session(session_id, exit_page=exit_page)
        if session:
            self.repo.create_event(
                session.visitor_id,
                session.id,
                event_name="session_end",
                page=exit_page,
                event_metadata={
                    "duration_seconds": session.duration_seconds,
                    "page_views": session.page_views,
                },
            )
        return session

    # ── Event tracking & Dynamic Lead Scoring ─────────────────────────

    def track_event(
        self,
        visitor_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        event_name: str,
        page: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VisitorEvent:
        """Log a single interaction event and dynamically update lead score if a lead exists."""
        event = self.repo.create_event(
            visitor_id,
            session_id,
            event_name=event_name,
            page=page,
            event_metadata=metadata,
        )

        # Update session pageview count for page_view events
        if event_name == "page_view":
            self.repo.heartbeat_session(
                session_id,
                current_page=page,
                page_views_delta=1,
            )

        # Connect visitor event to associated Lead (if enquiry submitted)
        lead = self.scoring_service.find_lead_for_visitor(visitor_id=visitor_id)
        if lead:
            if not self.scoring_service.is_event_farmed(visitor_id, event_name, metadata):
                delta = self.scoring_service.calculate_event_score(event_name, metadata)
                if delta > 0:
                    prev_score, new_score, actual_delta = self.scoring_service.apply_score_change(
                        lead, delta, reason=event_name
                    )
                    self.db.commit()
                    self.db.refresh(lead)
                    if actual_delta > 0:
                        emit_lead_score_updated(
                            lead,
                            previous_score=prev_score,
                            new_score=new_score,
                            delta=actual_delta,
                            reason=event_name.upper(),
                        )

        return event

    def track_events_batch(
        self,
        events_data: list[dict],
    ) -> list[VisitorEvent]:
        """Bulk-ingest events with anti-farming lead scoring per associated lead."""
        events = self.repo.create_events_batch(events_data)

        # Group by visitor_id
        visitor_events_map: dict[uuid.UUID, list[dict]] = {}
        for data in events_data:
            vid = data["visitor_id"]
            visitor_events_map.setdefault(vid, []).append(data)

        for vid, ev_list in visitor_events_map.items():
            lead = self.scoring_service.find_lead_for_visitor(visitor_id=vid)
            if not lead:
                continue

            total_delta = 0
            for ev in ev_list:
                ev_name = ev.get("event_name", "")
                ev_meta = ev.get("event_metadata")
                if not self.scoring_service.is_event_farmed(vid, ev_name, ev_meta):
                    total_delta += self.scoring_service.calculate_event_score(ev_name, ev_meta)

            if total_delta > 0:
                prev_score, new_score, actual_delta = self.scoring_service.apply_score_change(
                    lead, total_delta, reason="batch"
                )
                self.db.commit()
                self.db.refresh(lead)
                if actual_delta > 0:
                    emit_lead_score_updated(
                        lead,
                        previous_score=prev_score,
                        new_score=new_score,
                        delta=actual_delta,
                        reason="BATCH_EVENTS",
                    )

        return events
