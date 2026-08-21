import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.response import SuccessResponse
from app.schemas.visitor import (
    EventBatchRequest,
    EventBatchResponse,
    EventTrackRequest,
    SessionEndRequest,
    SessionHeartbeatRequest,
    SessionStartRequest,
    VisitorEventResponse,
    VisitorIdentifyRequest,
    VisitorIdentifyResponse,
    VisitorResponse,
    VisitorSessionResponse,
)
from app.services.tracking_service import TrackingService

router = APIRouter(
    prefix="/visitors",
    tags=["Visitors & Tracking"],
)


@router.post(
    "/identify",
    response_model=SuccessResponse[VisitorIdentifyResponse],
    status_code=status.HTTP_200_OK,
    summary="Identify or upsert a web visitor",
    description="Identify visitor by browser fingerprint. Creates a new visitor record or updates device/location data for existing visitors.",
)
def identify_visitor(
    payload: VisitorIdentifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip_address = payload.ip_address or (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")

    service = TrackingService(db)
    visitor, is_new = service.identify_visitor(
        fingerprint=payload.fingerprint,
        ip_address=ip_address,
        country=payload.country,
        state=payload.state,
        city=payload.city,
        browser=payload.browser or user_agent,
        os=payload.os,
        device=payload.device,
        customer_id=payload.customer_id,
    )

    return SuccessResponse(
        message="Visitor identified successfully",
        data=VisitorIdentifyResponse(
            visitor=VisitorResponse.model_validate(visitor),
            is_new=is_new,
        ),
    )


@router.post(
    "/sessions/start",
    response_model=SuccessResponse[VisitorSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Start a new visitor navigation session",
    description="Record a new web browsing session with landing page, referrer, and UTM campaign parameters.",
)
def create_session(
    payload: SessionStartRequest,
    db: Session = Depends(get_db),
):
    service = TrackingService(db)
    session = service.start_session(
        visitor_id=payload.visitor_id,
        landing_page=payload.landing_page,
        referrer=payload.referrer,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_term=payload.utm_term,
    )
    return SuccessResponse(
        message="Visitor session created successfully",
        data=VisitorSessionResponse.model_validate(session),
    )


@router.post(
    "/sessions/{session_id}/heartbeat",
    response_model=SuccessResponse[VisitorSessionResponse],
    summary="Session keep-alive heartbeat",
    description="Update exit page and page view count periodically during active session.",
)
def heartbeat_session(
    session_id: uuid.UUID,
    payload: SessionHeartbeatRequest,
    db: Session = Depends(get_db),
):
    service = TrackingService(db)
    session = service.heartbeat(
        session_id=session_id,
        current_page=payload.current_page,
        page_views_delta=payload.page_views_delta,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found",
        )

    return SuccessResponse(
        message="Session heartbeat recorded",
        data=VisitorSessionResponse.model_validate(session),
    )


@router.post(
    "/sessions/{session_id}/end",
    response_model=SuccessResponse[VisitorSessionResponse],
    summary="End visitor session",
    description="Finalise session, record final exit page, and compute total active session duration.",
)
def end_session(
    session_id: uuid.UUID,
    payload: SessionEndRequest,
    db: Session = Depends(get_db),
):
    service = TrackingService(db)
    session = service.end_session(
        session_id=session_id,
        exit_page=payload.exit_page,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found",
        )

    return SuccessResponse(
        message="Session ended successfully",
        data=VisitorSessionResponse.model_validate(session),
    )


@router.post(
    "/events",
    response_model=SuccessResponse[VisitorEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Log a single visitor event",
    description="Record interaction event (page view, tour package click, enquiry trigger). Dynamically updates visitor lead score.",
)
def log_event(
    payload: EventTrackRequest,
    db: Session = Depends(get_db),
):
    service = TrackingService(db)
    event = service.track_event(
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        event_name=payload.event_name,
        page=payload.page,
        metadata=payload.event_metadata,
    )

    return SuccessResponse(
        message="Visitor event logged successfully",
        data=VisitorEventResponse.model_validate(event),
    )


@router.post(
    "/events/batch",
    response_model=SuccessResponse[EventBatchResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Batch log multiple visitor interaction events",
    description="Bulk ingest analytics events buffered by frontend SDKs (up to 50 events per batch).",
)
def log_events_batch(
    payload: EventBatchRequest,
    db: Session = Depends(get_db),
):
    service = TrackingService(db)
    events_data = [item.model_dump() for item in payload.events]
    created_events = service.track_events_batch(events_data)

    return SuccessResponse(
        message=f"Successfully ingested {len(created_events)} visitor events",
        data=EventBatchResponse(
            accepted_count=len(created_events),
            events=[VisitorEventResponse.model_validate(e) for e in created_events],
        ),
    )

