"""Tracking service — orchestrates visitor identification, session
lifecycle, event tracking, and lead-score calculation.

Sits between the API layer and the repository layer, applying
business rules (scoring, session auto-events) that don't belong
in either.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.lead_scoring import calculate_score
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession
from app.repository.visitor_repo import VisitorRepository


class TrackingService:
    """High-level orchestration for the visitor analytics subsystem."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VisitorRepository(db)

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
        # Score the session start
        score_delta = calculate_score("session_start")
        self.repo.increment_lead_score(visitor_id, score_delta)
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

    # ── Event tracking ────────────────────────────────────────────────

    def track_event(
        self,
        visitor_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        event_name: str,
        page: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VisitorEvent:
        """Log a single interaction event and update lead score."""
        event = self.repo.create_event(
            visitor_id,
            session_id,
            event_name=event_name,
            page=page,
            event_metadata=metadata,
        )

        # Weighted lead scoring
        score_delta = calculate_score(event_name, metadata)
        self.repo.increment_lead_score(visitor_id, score_delta)

        # Update session pageview count for page_view events
        if event_name == "page_view":
            self.repo.heartbeat_session(
                session_id,
                current_page=page,
                page_views_delta=1,
            )

        return event

    def track_events_batch(
        self,
        events_data: list[dict],
    ) -> list[VisitorEvent]:
        """Bulk-ingest events with aggregated lead scoring.

        Each item in ``events_data`` must contain ``visitor_id``,
        ``session_id``, ``event_name`` and optionally ``page`` and
        ``event_metadata``.
        """
        events = self.repo.create_events_batch(events_data)

        # Aggregate score deltas per visitor
        visitor_scores: dict[uuid.UUID, int] = {}
        for data in events_data:
            vid = data["visitor_id"]
            delta = calculate_score(data["event_name"], data.get("event_metadata"))
            visitor_scores[vid] = visitor_scores.get(vid, 0) + delta

        for vid, total_delta in visitor_scores.items():
            self.repo.increment_lead_score(vid, total_delta)

        return events

