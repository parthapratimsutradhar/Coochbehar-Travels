import math
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.lead_scoring import get_event_category
from app.db.database import get_db
from app.models.user import User
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import SuccessResponse
from app.schemas.visitor import (
    AnalyticsOverviewResponse,
    FunnelStageItem,
    LeadScoreDistributionItem,
    TopEventItem,
    TopPageItem,
    UtmPerformanceItem,
    VisitorEventResponse,
    VisitorProfileResponse,
    VisitorResponse,
    VisitorSessionResponse,
)

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin - Analytics & Visitor Intelligence"],
)


@router.get(
    "/overview",
    response_model=SuccessResponse[AnalyticsOverviewResponse],
    summary="Get real-time analytics KPI overview",
    description="Returns top-level telemetry metrics: visitors today, active sessions, events today, avg lead score.",
)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    # 1. Total visitors
    total_visitors = db.execute(select(func.count(Visitor.id))).scalar_one() or 0

    # 2. Visitors today
    visitors_today = (
        db.execute(
            select(func.count(Visitor.id)).where(Visitor.first_seen >= today_start)
        ).scalar_one()
        or 0
    )

    # 3. Active sessions (ended_at is NULL and started within last 30 min)
    session_cutoff = now - timedelta(minutes=30)
    active_sessions = (
        db.execute(
            select(func.count(VisitorSession.id)).where(
                VisitorSession.ended_at.is_(None),
                VisitorSession.started_at >= session_cutoff,
            )
        ).scalar_one()
        or 0
    )

    # 4. Total events today
    events_today = (
        db.execute(
            select(func.count(VisitorEvent.id)).where(
                VisitorEvent.created_at >= today_start
            )
        ).scalar_one()
        or 0
    )

    # 5. Average lead score
    avg_score = (
        db.execute(select(func.avg(Visitor.lead_score))).scalar_one() or 0.0
    )

    # 6. High-intent visitors count (lead_score >= 20)
    high_intent_count = (
        db.execute(
            select(func.count(Visitor.id)).where(Visitor.lead_score >= 20)
        ).scalar_one()
        or 0
    )

    return SuccessResponse(
        message="Analytics overview fetched successfully",
        data=AnalyticsOverviewResponse(
            total_visitors=total_visitors,
            visitors_today=visitors_today,
            active_sessions=active_sessions,
            total_events_today=events_today,
            average_lead_score=round(float(avg_score), 2),
            high_intent_visitors_count=high_intent_count,
        ),
    )


@router.get(
    "/visitors",
    response_model=PaginatedResponse[VisitorResponse],
    summary="List and filter tracked web visitors",
    description="Retrieve paginated visitor records with lead scores, location data, search, and min-score filters.",
)
def list_visitors(
    min_score: int | None = Query(None, ge=0, description="Filter visitors with lead score >= min_score"),
    search: str | None = Query(None, description="Search by fingerprint, ip, city, country, browser, os"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    stmt = select(Visitor).order_by(Visitor.last_seen.desc())

    if min_score is not None:
        stmt = stmt.where(Visitor.lead_score >= min_score)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (Visitor.fingerprint.ilike(search_pattern))
            | (Visitor.ip_address.ilike(search_pattern))
            | (Visitor.city.ilike(search_pattern))
            | (Visitor.country.ilike(search_pattern))
            | (Visitor.browser.ilike(search_pattern))
            | (Visitor.os.ilike(search_pattern))
        )

    # Count total for pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_items = db.execute(count_stmt).scalar_one()

    total_pages = max(1, math.ceil(total_items / page_size))
    offset = (page - 1) * page_size

    visitors = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()

    return PaginatedResponse(
        message="Visitors fetched successfully",
        data=[VisitorResponse.model_validate(v) for v in visitors],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get(
    "/visitors/{visitor_id}",
    response_model=SuccessResponse[VisitorProfileResponse],
    summary="Get detailed visitor profile for admin review",
)
def get_visitor_details(
    visitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    stmt_vis = select(Visitor).where(Visitor.id == visitor_id)
    visitor = db.execute(stmt_vis).scalar_one_or_none()
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visitor with ID {visitor_id} not found",
        )

    stmt_sess = (
        select(VisitorSession)
        .where(VisitorSession.visitor_id == visitor_id)
        .order_by(VisitorSession.started_at.desc())
    )
    sessions = db.execute(stmt_sess).scalars().all()

    stmt_evt = (
        select(VisitorEvent)
        .where(VisitorEvent.visitor_id == visitor_id)
        .order_by(VisitorEvent.created_at.desc())
        .limit(50)
    )
    recent_events = db.execute(stmt_evt).scalars().all()

    total_events = (
        db.execute(
            select(func.count(VisitorEvent.id)).where(VisitorEvent.visitor_id == visitor_id)
        ).scalar_one()
        or 0
    )

    return SuccessResponse(
        message="Visitor details retrieved successfully",
        data=VisitorProfileResponse(
            visitor=VisitorResponse.model_validate(visitor),
            sessions=[VisitorSessionResponse.model_validate(s) for s in sessions],
            recent_events=[VisitorEventResponse.model_validate(e) for e in recent_events],
            total_events=total_events,
            total_sessions=len(sessions),
        ),
    )


@router.get(
    "/top-pages",
    response_model=SuccessResponse[list[TopPageItem]],
    summary="Top pages by total views & unique visitors",
)
def get_top_pages(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Top N pages"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            VisitorEvent.page.label("page"),
            func.count(VisitorEvent.id).label("views"),
            func.count(func.distinct(VisitorEvent.visitor_id)).label("unique_visitors"),
        )
        .where(
            VisitorEvent.page.is_not(None),
            VisitorEvent.created_at >= cutoff,
        )
        .group_by(VisitorEvent.page)
        .order_by(func.count(VisitorEvent.id).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()
    items = [
        TopPageItem(
            page=row.page or "/",
            views=row.views,
            unique_visitors=row.unique_visitors,
        )
        for row in results
    ]

    return SuccessResponse(
        message="Top pages fetched successfully",
        data=items,
    )


@router.get(
    "/top-events",
    response_model=SuccessResponse[list[TopEventItem]],
    summary="Top telemetry event types by frequency",
)
def get_top_events(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(15, ge=1, le=50, description="Top N event types"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            VisitorEvent.event_name,
            func.count(VisitorEvent.id).label("count"),
        )
        .where(VisitorEvent.created_at >= cutoff)
        .group_by(VisitorEvent.event_name)
        .order_by(func.count(VisitorEvent.id).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()
    items = [
        TopEventItem(
            event_name=row.event_name,
            count=row.count,
            category=get_event_category(row.event_name),
        )
        for row in results
    ]

    return SuccessResponse(
        message="Top events fetched successfully",
        data=items,
    )


@router.get(
    "/utm-performance",
    response_model=SuccessResponse[list[UtmPerformanceItem]],
    summary="UTM marketing campaign performance analytics",
)
def get_utm_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            VisitorSession.utm_source,
            VisitorSession.utm_medium,
            VisitorSession.utm_campaign,
            func.count(VisitorSession.id).label("session_count"),
            func.avg(VisitorSession.duration_seconds).label("avg_duration"),
        )
        .where(
            VisitorSession.started_at >= cutoff,
            (VisitorSession.utm_source.is_not(None))
            | (VisitorSession.utm_medium.is_not(None))
            | (VisitorSession.utm_campaign.is_not(None)),
        )
        .group_by(
            VisitorSession.utm_source,
            VisitorSession.utm_medium,
            VisitorSession.utm_campaign,
        )
        .order_by(func.count(VisitorSession.id).desc())
        .limit(20)
    )

    results = db.execute(stmt).all()
    items: list[UtmPerformanceItem] = []

    for row in results:
        # Count conversions (enquiry events) for this UTM combination
        sub_stmt = (
            select(func.count(VisitorEvent.id))
            .join(VisitorSession, VisitorEvent.session_id == VisitorSession.id)
            .where(
                VisitorSession.utm_source == row.utm_source,
                VisitorSession.utm_medium == row.utm_medium,
                VisitorSession.utm_campaign == row.utm_campaign,
                VisitorEvent.event_name.in_(["enquiry_submit", "booking_enquiry", "custom_tour_request"]),
            )
        )
        conversions = db.execute(sub_stmt).scalar_one() or 0

        items.append(
            UtmPerformanceItem(
                utm_source=row.utm_source,
                utm_medium=row.utm_medium,
                utm_campaign=row.utm_campaign,
                session_count=row.session_count,
                conversion_count=conversions,
                avg_duration_seconds=round(float(row.avg_duration or 0), 1),
            )
        )

    return SuccessResponse(
        message="UTM performance fetched successfully",
        data=items,
    )


@router.get(
    "/lead-score-distribution",
    response_model=SuccessResponse[list[LeadScoreDistributionItem]],
    summary="Lead score distribution breakdown",
)
def get_lead_score_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    ranges = [
        ("0-5 (Cold)", 0, 5),
        ("6-15 (Warm)", 6, 15),
        ("16-30 (Hot)", 16, 30),
        ("31+ (Highly Qualified)", 31, 999999),
    ]

    items: list[LeadScoreDistributionItem] = []
    for label, min_val, max_val in ranges:
        stmt = select(func.count(Visitor.id)).where(
            Visitor.lead_score >= min_val,
            Visitor.lead_score <= max_val,
        )
        cnt = db.execute(stmt).scalar_one() or 0
        items.append(LeadScoreDistributionItem(score_range=label, count=cnt))

    return SuccessResponse(
        message="Lead score distribution fetched successfully",
        data=items,
    )


@router.get(
    "/funnel",
    response_model=SuccessResponse[list[FunnelStageItem]],
    summary="Conversion funnel analytics",
    description="Tracks drop-off across 4 key stages: All Visitors → Package Viewers → Enquiry Initiated → Submitted.",
)
def get_conversion_funnel(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_staff),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Total unique visitors in period
    v1 = db.execute(
        select(func.count(Visitor.id)).where(Visitor.first_seen >= cutoff)
    ).scalar_one() or 0

    # 2. Package Viewers (unique visitors who viewed package/variant)
    v2 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= cutoff,
            VisitorEvent.event_name.in_(["tour_package_view", "tour_variant_view"]),
        )
    ).scalar_one() or 0

    # 3. Enquiry Initiated (opened/filled enquiry form)
    v3 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= cutoff,
            VisitorEvent.event_name.in_(["enquiry_form_open", "enquiry_form_fill", "whatsapp_click"]),
        )
    ).scalar_one() or 0

    # 4. Submitted Enquiry (converted)
    v4 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= cutoff,
            VisitorEvent.event_name.in_(["enquiry_submit", "booking_enquiry", "custom_tour_request"]),
        )
    ).scalar_one() or 0

    base_count = max(1, v1)

    items = [
        FunnelStageItem(stage="1. Total Visitors", visitor_count=v1, conversion_rate=100.0),
        FunnelStageItem(stage="2. Package Viewers", visitor_count=v2, conversion_rate=round((v2 / base_count) * 100, 1)),
        FunnelStageItem(stage="3. Form / Intent Initiated", visitor_count=v3, conversion_rate=round((v3 / base_count) * 100, 1)),
        FunnelStageItem(stage="4. Enquiry Submitted", visitor_count=v4, conversion_rate=round((v4 / base_count) * 100, 1)),
    ]

    return SuccessResponse(
        message="Conversion funnel fetched successfully",
        data=items,
    )
