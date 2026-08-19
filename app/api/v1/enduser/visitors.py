import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession
from app.schemas.response import SuccessResponse
from app.schemas.visitor import (
    VisitorCreate,
    VisitorEventCreate,
    VisitorEventResponse,
    VisitorResponse,
    VisitorSessionCreate,
    VisitorSessionResponse,
)

router = APIRouter(
    prefix="/visitors",
    tags=["Visitors & Telemetry"],
)


@router.post(
    "",
    response_model=SuccessResponse[VisitorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Track or identify a web visitor",
    description="Initialize a new visitor tracking ID or update last_seen for an existing visitor fingerprint.",
)
def track_visitor(
    payload: VisitorCreate,
    db: Session = Depends(get_db),
):
    visitor = None
    if payload.fingerprint:
        stmt = select(Visitor).where(Visitor.fingerprint == payload.fingerprint)
        visitor = db.execute(stmt).scalar_one_or_none()

    if visitor:
        visitor.last_seen = datetime.now()
        if payload.customer_id and not visitor.customer_id:
            visitor.customer_id = payload.customer_id
        db.commit()
        db.refresh(visitor)
        return SuccessResponse(
            message="Visitor updated successfully",
            data=VisitorResponse.model_validate(visitor),
        )

    visitor_code = f"VIS-{uuid.uuid4().hex[:8].upper()}"
    visitor = Visitor(
        visitor_code=visitor_code,
        fingerprint=payload.fingerprint,
        ip_address=payload.ip_address,
        country=payload.country,
        state=payload.state,
        city=payload.city,
        browser=payload.browser,
        os=payload.os,
        device=payload.device,
        customer_id=payload.customer_id,
        lead_score=payload.lead_score,
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return SuccessResponse(
        message="Visitor tracked successfully",
        data=VisitorResponse.model_validate(visitor),
    )


@router.post(
    "/sessions",
    response_model=SuccessResponse[VisitorSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Start a visitor session",
    description="Record a new web browsing session for a visitor.",
)
def create_session(
    payload: VisitorSessionCreate,
    db: Session = Depends(get_db),
):
    session_code = f"SES-{uuid.uuid4().hex[:8].upper()}"
    session = VisitorSession(
        session_code=session_code,
        visitor_id=payload.visitor_id,
        landing_page=payload.landing_page,
        exit_page=payload.exit_page,
        referrer=payload.referrer,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_term=payload.utm_term,
        page_views=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SuccessResponse(
        message="Visitor session created successfully",
        data=VisitorSessionResponse.model_validate(session),
    )


@router.post(
    "/events",
    response_model=SuccessResponse[VisitorEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Log visitor interaction event",
    description="Record telemetry events (page clicks, tour package views, form submissions).",
)
def log_event(
    payload: VisitorEventCreate,
    db: Session = Depends(get_db),
):
    event_code = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    event = VisitorEvent(
        event_code=event_code,
        visitor_id=payload.visitor_id,
        session_id=payload.session_id,
        event_name=payload.event_name,
        page=payload.page,
        event_metadata=payload.event_metadata,
    )
    db.add(event)

    # Increment visitor lead score based on engagement
    stmt = select(Visitor).where(Visitor.id == payload.visitor_id)
    visitor = db.execute(stmt).scalar_one_or_none()
    if visitor:
        visitor.lead_score += 5
        visitor.last_seen = datetime.now()

    # Increment session page views if page view event
    stmt_sess = select(VisitorSession).where(VisitorSession.id == payload.session_id)
    session = db.execute(stmt_sess).scalar_one_or_none()
    if session:
        session.page_views += 1
        if payload.page:
            session.exit_page = payload.page

    db.commit()
    db.refresh(event)
    return SuccessResponse(
        message="Visitor event logged successfully",
        data=VisitorEventResponse.model_validate(event),
    )

