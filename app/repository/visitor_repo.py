"""Repository for visitor, session, and event data access.

Follows the established repository pattern used by ``CustomerRepository``
and ``AuthSessionRepository``.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession


class VisitorRepository:
    """Data-access layer for the web-visitor telemetry subsystem."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Visitor CRUD ──────────────────────────────────────────────────

    def get_by_id(self, visitor_id: uuid.UUID) -> Visitor | None:
        """Fetch a visitor by primary-key UUID."""
        stmt = select(Visitor).where(Visitor.id == visitor_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_fingerprint(self, fingerprint: str) -> Visitor | None:
        """Fetch a visitor by browser fingerprint."""
        stmt = select(Visitor).where(Visitor.fingerprint == fingerprint)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self,
        fingerprint: str | None,
        *,
        ip_address: str | None = None,
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
        browser: str | None = None,
        os: str | None = None,
        device: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[Visitor, bool]:
        """Upsert a visitor by fingerprint.

        Returns ``(visitor, is_new)`` — ``is_new`` is True when a fresh
        record was created.
        """
        if fingerprint:
            existing = self.get_by_fingerprint(fingerprint)
            if existing:
                # Refresh last_seen and merge any new geo/device data
                existing.last_seen = datetime.now(timezone.utc)
                if ip_address and not existing.ip_address:
                    existing.ip_address = ip_address
                if country and not existing.country:
                    existing.country = country
                if state and not existing.state:
                    existing.state = state
                if city and not existing.city:
                    existing.city = city
                if browser and not existing.browser:
                    existing.browser = browser
                if os and not existing.os:
                    existing.os = os
                if device and not existing.device:
                    existing.device = device
                if customer_id and not existing.customer_id:
                    existing.customer_id = customer_id
                self.db.commit()
                self.db.refresh(existing)
                return existing, False

        visitor_code = f"VIS-{uuid.uuid4().hex[:8].upper()}"
        visitor = Visitor(
            visitor_code=visitor_code,
            fingerprint=fingerprint,
            ip_address=ip_address,
            country=country,
            state=state,
            city=city,
            browser=browser,
            os=os,
            device=device,
            customer_id=customer_id,
        )
        self.db.add(visitor)
        self.db.commit()
        self.db.refresh(visitor)
        return visitor, True

    def update_last_seen(self, visitor_id: uuid.UUID) -> None:
        """Touch the visitor's ``last_seen`` timestamp."""
        stmt = (
            update(Visitor)
            .where(Visitor.id == visitor_id)
            .values(last_seen=datetime.now(timezone.utc))
        )
        self.db.execute(stmt)
        self.db.commit()

    def link_to_customer(
        self, visitor_id: uuid.UUID, customer_id: uuid.UUID
    ) -> None:
        """Associate a visitor with a customer identity."""
        stmt = (
            update(Visitor)
            .where(Visitor.id == visitor_id)
            .values(customer_id=customer_id)
        )
        self.db.execute(stmt)
        self.db.commit()

    # ── Sessions ──────────────────────────────────────────────────────

    def create_session(
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
        """Create a new browsing session."""
        session = VisitorSession(
            visitor_id=visitor_id,
            landing_page=landing_page,
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_term=utm_term,
            page_views=1,
            duration_seconds=0,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session_by_id(self, session_id: uuid.UUID) -> VisitorSession | None:
        """Fetch a session by ID."""
        stmt = select(VisitorSession).where(VisitorSession.id == session_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def heartbeat_session(
        self,
        session_id: uuid.UUID,
        *,
        current_page: str | None = None,
        page_views_delta: int = 0,
    ) -> VisitorSession | None:
        """Keep-alive: update exit page and increment page-view counter."""
        session = self.get_session_by_id(session_id)
        if not session:
            return None

        if current_page:
            session.exit_page = current_page
        if page_views_delta > 0:
            session.page_views += page_views_delta

        # Update duration from started_at → now
        if session.started_at:
            now = datetime.now(timezone.utc)
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            session.duration_seconds = int((now - started).total_seconds())

        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(
        self,
        session_id: uuid.UUID,
        *,
        exit_page: str | None = None,
    ) -> VisitorSession | None:
        """Finalise a session: set ended_at, compute duration, set exit page."""
        session = self.get_session_by_id(session_id)
        if not session:
            return None

        now = datetime.now(timezone.utc)
        session.ended_at = now
        if exit_page:
            session.exit_page = exit_page

        if session.started_at:
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            session.duration_seconds = int((now - started).total_seconds())

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_sessions_by_visitor(
        self, visitor_id: uuid.UUID
    ) -> list[VisitorSession]:
        """All sessions for a visitor, most-recent first."""
        stmt = (
            select(VisitorSession)
            .where(VisitorSession.visitor_id == visitor_id)
            .order_by(VisitorSession.started_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Events ────────────────────────────────────────────────────────

    def create_event(
        self,
        visitor_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        event_name: str,
        page: str | None = None,
        event_metadata: dict | None = None,
    ) -> VisitorEvent:
        """Log a single visitor interaction event."""
        event = VisitorEvent(
            visitor_id=visitor_id,
            session_id=session_id,
            event_name=event_name,
            page=page,
            event_metadata=event_metadata,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def create_events_batch(
        self,
        events_data: list[dict],
    ) -> list[VisitorEvent]:
        """Bulk-insert multiple events in a single transaction."""
        created: list[VisitorEvent] = []
        for data in events_data:
            event = VisitorEvent(
                visitor_id=data["visitor_id"],
                session_id=data["session_id"],
                event_name=data["event_name"],
                page=data.get("page"),
                event_metadata=data.get("event_metadata"),
            )
            self.db.add(event)
            created.append(event)

        self.db.commit()
        for event in created:
            self.db.refresh(event)
        return created

    def get_events_by_session(
        self, session_id: uuid.UUID
    ) -> list[VisitorEvent]:
        """Events for a specific session, chronological order."""
        stmt = (
            select(VisitorEvent)
            .where(VisitorEvent.session_id == session_id)
            .order_by(VisitorEvent.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_events_by_visitor(
        self,
        visitor_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VisitorEvent]:
        """Paginated events for a visitor, most-recent first."""
        stmt = (
            select(VisitorEvent)
            .where(VisitorEvent.visitor_id == visitor_id)
            .order_by(VisitorEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_events_by_visitor(self, visitor_id: uuid.UUID) -> int:
        """Total event count for pagination metadata."""
        stmt = (
            select(func.count())
            .select_from(VisitorEvent)
            .where(VisitorEvent.visitor_id == visitor_id)
        )
        return self.db.execute(stmt).scalar_one()
