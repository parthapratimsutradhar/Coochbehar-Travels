"""Admin analytics API — visitor intelligence, live stats, traffic sources,
location rankings, date-filtered statistics and UTM performance.
"""
import math
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, literal, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.lead_scoring import get_event_category
from app.db.database import get_db
from app.models.lead import Lead
from app.models.account import Account
from app.models.visitor import Visitor
from app.models.visitor_event import VisitorEvent
from app.models.visitor_session import VisitorSession
from app.realtime.presence import ACTIVE_VISITORS, get_live_counts
from app.schemas.analytics import SuperAdminDashboardResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import SuccessResponse
from app.schemas.visitor import (
    AnalyticsOverviewResponse,
    AnalyticsStatsResponse,
    FunnelStageItem,
    LeadScoreDistributionItem,
    LiveStatsResponse,
    LiveVisitorItem,
    LocationRankItem,
    TopEventItem,
    TopPageItem,
    TrafficSourceItem,
    UtmPerformanceItem,
    VisitorEventResponse,
    VisitorProfileResponse,
    VisitorResponse,
    VisitorSessionResponse,
)
from app.services.cleanup_service import cleanup_old_data
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin - Analytics & Visitor Intelligence"],
)

DateFilterLiteral = Literal["today", "yesterday", "7d", "30d", "90d"]


def _date_range(date_filter: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for a date filter string."""
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    if date_filter == "today":
        return today_start, today_end
    if date_filter == "yesterday":
        y = today_start - timedelta(days=1)
        return y, today_start
    if date_filter == "7d":
        return today_start - timedelta(days=7), today_end
    if date_filter == "30d":
        return today_start - timedelta(days=30), today_end
    if date_filter == "90d":
        return today_start - timedelta(days=90), today_end
    # fallback
    return today_start - timedelta(days=30), today_end


def _classify_source_sql(referrer_col, utm_source_col, utm_medium_col):
    """SQLAlchemy case() expression for classifying traffic source."""
    return case(
        (
            and_(utm_medium_col.isnot(None), utm_medium_col.in_(["cpc", "ppc", "paid", "paidsearch", "paid_social"])),
            "paid",
        ),
        (
            and_(utm_medium_col.isnot(None), utm_medium_col.in_(["email", "newsletter"])),
            "email",
        ),
        (
            and_(
                utm_medium_col.isnot(None),
                utm_medium_col == "social",
            ),
            "social",
        ),
        (
            and_(utm_source_col.isnot(None)),
            "utm_campaign",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%google.%"),
            ),
            "organic",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%bing.%"),
            ),
            "organic",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%facebook.com%"),
            ),
            "social",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%instagram.com%"),
            ),
            "social",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%twitter.com%"),
            ),
            "social",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%linkedin.com%"),
            ),
            "social",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.ilike("%youtube.com%"),
            ),
            "social",
        ),
        (
            and_(
                referrer_col.isnot(None),
                referrer_col.isnot(None),
            ),
            "referral",
        ),
        else_="direct",
    )


# ── Live Presence ─────────────────────────────────────────────────────

@router.get(
    "/live",
    response_model=SuccessResponse[LiveStatsResponse],
    summary="Get live visitor/customer counts and presence data",
    description="Returns real-time counts of active visitors and customers plus their detailed presence data (page, location, device). Optionally filter by type.",
)
def get_live_stats(
    visitor_type: str | None = Query(None, description="Filter: 'customer' or 'visitor'. Omit for all."),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    counts = get_live_counts()
    visitors_list = list(ACTIVE_VISITORS.values())

    if visitor_type in ("customer", "visitor"):
        visitors_list = [
            v for v in visitors_list
            if v.get("visitor_type") == visitor_type
            or (visitor_type == "customer" and v.get("customer_id"))
            or (visitor_type == "visitor" and not v.get("customer_id"))
        ]

    from datetime import datetime, timezone
    items = [LiveVisitorItem(**{k: v for k, v in vis.items() if k in LiveVisitorItem.model_fields}) for vis in visitors_list]

    return SuccessResponse(
        message="Live stats fetched successfully",
        data=LiveStatsResponse(
            total=counts["total"],
            customers=counts["customers"],
            visitors=counts["visitors"],
            active_visitors=items,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


# ── Date-filtered statistics ──────────────────────────────────────────

@router.get(
    "/stats",
    response_model=SuccessResponse[AnalyticsStatsResponse],
    summary="Get date-filtered analytics statistics",
    description="Statistical overview for a date period: total visitors, customers, anonymous visitors, events, page views, sessions, avg session duration, avg pages per session.",
)
def get_analytics_stats(
    date_filter: DateFilterLiteral = Query("7d", description="today | yesterday | 7d | 30d | 90d"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    # Visitors in period
    total_visitors = db.execute(
        select(func.count(func.distinct(Visitor.id))).where(
            Visitor.first_seen >= start, Visitor.first_seen <= end
        )
    ).scalar_one() or 0

    # Customers (visitors linked to an account)
    total_customers = db.execute(
        select(func.count(func.distinct(Visitor.id))).where(
            Visitor.first_seen >= start,
            Visitor.first_seen <= end,
            Visitor.customer_id.isnot(None),
        )
    ).scalar_one() or 0

    # Events in period
    total_events = db.execute(
        select(func.count(VisitorEvent.id)).where(
            VisitorEvent.created_at >= start, VisitorEvent.created_at <= end
        )
    ).scalar_one() or 0

    # Page views in period
    total_page_views = db.execute(
        select(func.count(VisitorEvent.id)).where(
            VisitorEvent.created_at >= start,
            VisitorEvent.created_at <= end,
            VisitorEvent.event_name == "page_view",
        )
    ).scalar_one() or 0

    # Sessions in period
    session_stats = db.execute(
        select(
            func.count(VisitorSession.id).label("session_count"),
            func.coalesce(func.avg(VisitorSession.duration_seconds), 0).label("avg_duration"),
            func.coalesce(func.avg(VisitorSession.page_views), 0).label("avg_page_views"),
        ).where(
            VisitorSession.started_at >= start, VisitorSession.started_at <= end
        )
    ).one()

    return SuccessResponse(
        message="Analytics stats fetched successfully",
        data=AnalyticsStatsResponse(
            total_visitors=total_visitors,
            total_customers=total_customers,
            total_anonymous_visitors=total_visitors - total_customers,
            total_events=total_events,
            total_page_views=total_page_views,
            total_sessions=session_stats.session_count or 0,
            avg_session_duration_seconds=round(float(session_stats.avg_duration or 0), 1),
            avg_page_views_per_session=round(float(session_stats.avg_page_views or 0), 2),
            date_filter=date_filter,
            period_start=start.isoformat(),
            period_end=end.isoformat(),
        ),
    )


# ── Overview (legacy + enhanced) ─────────────────────────────────────

@router.get(
    "/overview",
    response_model=SuccessResponse[AnalyticsOverviewResponse],
    summary="Get real-time analytics KPI overview",
    description="Returns top-level telemetry metrics: visitors today, active sessions, events today, avg lead score.",
)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    total_visitors = db.execute(select(func.count(Visitor.id))).scalar_one() or 0
    visitors_today = db.execute(
        select(func.count(Visitor.id)).where(Visitor.first_seen >= today_start)
    ).scalar_one() or 0

    session_cutoff = now - timedelta(minutes=30)
    active_sessions = db.execute(
        select(func.count(VisitorSession.id)).where(
            VisitorSession.ended_at.is_(None),
            VisitorSession.started_at >= session_cutoff,
        )
    ).scalar_one() or 0

    events_today = db.execute(
        select(func.count(VisitorEvent.id)).where(VisitorEvent.created_at >= today_start)
    ).scalar_one() or 0

    avg_score = db.execute(select(func.avg(Lead.lead_score))).scalar_one() or 0.0
    high_intent_count = db.execute(
        select(func.count(Lead.id)).where(Lead.lead_score >= 20)
    ).scalar_one() or 0

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


# ── Visitors list ─────────────────────────────────────────────────────

@router.get(
    "/visitors",
    response_model=PaginatedResponse[VisitorResponse],
    summary="List and filter tracked web visitors",
    description="Retrieve paginated visitor records. Filter by type (customer/visitor), date, and search.",
)
def list_visitors(
    visitor_type: str | None = Query(None, description="Filter: 'customer' or 'visitor'"),
    date_filter: DateFilterLiteral | None = Query(None, description="today | yesterday | 7d | 30d | 90d"),
    search: str | None = Query(None, description="Search by fingerprint, ip, city, country, browser, os"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    stmt = select(Visitor).order_by(Visitor.last_seen.desc())

    if visitor_type == "customer":
        stmt = stmt.where(Visitor.customer_id.isnot(None))
    elif visitor_type == "visitor":
        stmt = stmt.where(Visitor.customer_id.is_(None))

    if date_filter:
        start, end = _date_range(date_filter)
        stmt = stmt.where(Visitor.first_seen >= start, Visitor.first_seen <= end)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (Visitor.fingerprint.ilike(pattern))
            | (Visitor.ip_address.ilike(pattern))
            | (Visitor.city.ilike(pattern))
            | (Visitor.country.ilike(pattern))
            | (Visitor.browser.ilike(pattern))
            | (Visitor.os.ilike(pattern))
        )

    total_items = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
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
    summary="Get detailed visitor profile",
    description="Get full visitor profile with all sessions and recent events. Uniquely identifiable via visitor_code.",
)
def get_visitor_details(
    visitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    visitor = db.execute(select(Visitor).where(Visitor.id == visitor_id)).scalar_one_or_none()
    if not visitor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visitor {visitor_id} not found")

    sessions = db.execute(
        select(VisitorSession)
        .where(VisitorSession.visitor_id == visitor_id)
        .order_by(VisitorSession.started_at.desc())
    ).scalars().all()

    recent_events = db.execute(
        select(VisitorEvent)
        .where(VisitorEvent.visitor_id == visitor_id)
        .order_by(VisitorEvent.created_at.desc())
        .limit(50)
    ).scalars().all()

    total_events = db.execute(
        select(func.count(VisitorEvent.id)).where(VisitorEvent.visitor_id == visitor_id)
    ).scalar_one() or 0

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


# ── Top Pages ─────────────────────────────────────────────────────────

@router.get(
    "/top-pages",
    response_model=SuccessResponse[list[TopPageItem]],
    summary="Top pages by total views & unique visitors",
    description="Ranked list of most visited pages. Supports date filtering.",
)
def get_top_pages(
    date_filter: DateFilterLiteral = Query("30d", description="today | yesterday | 7d | 30d | 90d"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    stmt = (
        select(
            VisitorEvent.page.label("page"),
            func.count(VisitorEvent.id).label("views"),
            func.count(func.distinct(VisitorEvent.visitor_id)).label("unique_visitors"),
        )
        .where(
            VisitorEvent.page.isnot(None),
            VisitorEvent.created_at >= start,
            VisitorEvent.created_at <= end,
            VisitorEvent.event_name == "page_view",
        )
        .group_by(VisitorEvent.page)
        .order_by(func.count(VisitorEvent.id).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()
    items = [
        TopPageItem(page=row.page or "/", views=row.views, unique_visitors=row.unique_visitors, rank=i + 1)
        for i, row in enumerate(results)
    ]

    return SuccessResponse(message="Top pages fetched successfully", data=items)


# ── Traffic Sources ────────────────────────────────────────────────────

@router.get(
    "/traffic-sources",
    response_model=SuccessResponse[list[TrafficSourceItem]],
    summary="Traffic source ranking",
    description="Breakdown of traffic sources: direct, organic, social, referral, paid, email, utm_campaign. Supports date filtering.",
)
def get_traffic_sources(
    date_filter: DateFilterLiteral = Query("30d", description="today | yesterday | 7d | 30d | 90d"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    source_expr = _classify_source_sql(
        VisitorSession.referrer,
        VisitorSession.utm_source,
        VisitorSession.utm_medium,
    )

    stmt = (
        select(
            source_expr.label("source"),
            func.count(VisitorSession.id).label("sessions"),
            func.count(func.distinct(VisitorSession.visitor_id)).label("visitors"),
        )
        .where(VisitorSession.started_at >= start, VisitorSession.started_at <= end)
        .group_by(source_expr)
        .order_by(func.count(VisitorSession.id).desc())
    )

    results = db.execute(stmt).all()
    total_sessions = sum(r.sessions for r in results) or 1

    items = [
        TrafficSourceItem(
            source=row.source or "direct",
            sessions=row.sessions,
            visitors=row.visitors,
            percentage=round((row.sessions / total_sessions) * 100, 1),
        )
        for row in results
    ]

    return SuccessResponse(message="Traffic sources fetched successfully", data=items)


# ── Location Rankings ─────────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=SuccessResponse[list[LocationRankItem]],
    summary="Location ranking by visitor/customer activity",
    description="Shows which countries and cities send the most visitors and customers. Supports date filtering and granularity (country/city).",
)
def get_location_ranking(
    date_filter: DateFilterLiteral = Query("30d", description="today | yesterday | 7d | 30d | 90d"),
    granularity: Literal["country", "city"] = Query("country", description="country or city"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    if granularity == "country":
        location_col = Visitor.country
    else:
        location_col = Visitor.city

    stmt = (
        select(
            location_col.label("location"),
            func.count(func.distinct(Visitor.id)).label("total"),
            func.count(func.distinct(
                case((Visitor.customer_id.isnot(None), Visitor.id), else_=None)
            )).label("customers"),
        )
        .where(
            location_col.isnot(None),
            Visitor.first_seen >= start,
            Visitor.first_seen <= end,
        )
        .group_by(location_col)
        .order_by(func.count(func.distinct(Visitor.id)).desc())
        .limit(limit)
    )

    results = db.execute(stmt).all()
    grand_total = sum(r.total for r in results) or 1

    items = [
        LocationRankItem(
            location=row.location,
            location_type=granularity,
            visitors=row.total - row.customers,
            customers=row.customers,
            total=row.total,
            percentage=round((row.total / grand_total) * 100, 1),
            rank=i + 1,
        )
        for i, row in enumerate(results)
    ]

    return SuccessResponse(message="Location ranking fetched successfully", data=items)


# ── UTM Performance ───────────────────────────────────────────────────

@router.get(
    "/utm-performance",
    response_model=SuccessResponse[list[UtmPerformanceItem]],
    summary="UTM marketing campaign performance analytics",
    description="UTM parameters tracked: utm_source, utm_medium, utm_campaign, utm_term, utm_content. Includes conversion count.",
)
def get_utm_performance(
    date_filter: DateFilterLiteral = Query("30d"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    stmt = (
        select(
            VisitorSession.utm_source,
            VisitorSession.utm_medium,
            VisitorSession.utm_campaign,
            func.count(VisitorSession.id).label("session_count"),
            func.avg(VisitorSession.duration_seconds).label("avg_duration"),
        )
        .where(
            VisitorSession.started_at >= start,
            VisitorSession.started_at <= end,
            (VisitorSession.utm_source.isnot(None))
            | (VisitorSession.utm_medium.isnot(None))
            | (VisitorSession.utm_campaign.isnot(None)),
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
        conversions = db.execute(
            select(func.count(VisitorEvent.id))
            .join(VisitorSession, VisitorEvent.session_id == VisitorSession.id)
            .where(
                VisitorSession.utm_source == row.utm_source,
                VisitorSession.utm_medium == row.utm_medium,
                VisitorSession.utm_campaign == row.utm_campaign,
                VisitorEvent.event_name.in_(["enquiry_submit", "booking_enquiry", "custom_tour_request"]),
            )
        ).scalar_one() or 0

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

    return SuccessResponse(message="UTM performance fetched successfully", data=items)


# ── Top Events ────────────────────────────────────────────────────────

@router.get(
    "/top-events",
    response_model=SuccessResponse[list[TopEventItem]],
    summary="Top telemetry event types by frequency",
)
def get_top_events(
    date_filter: DateFilterLiteral = Query("30d"),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    stmt = (
        select(
            VisitorEvent.event_name,
            func.count(VisitorEvent.id).label("count"),
        )
        .where(VisitorEvent.created_at >= start, VisitorEvent.created_at <= end)
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

    return SuccessResponse(message="Top events fetched successfully", data=items)


# ── Lead Score Distribution ───────────────────────────────────────────

@router.get(
    "/lead-score-distribution",
    response_model=SuccessResponse[list[LeadScoreDistributionItem]],
    summary="Lead score distribution breakdown",
)
def get_lead_score_distribution(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    ranges = [
        ("0-5 (Cold)", 0, 5),
        ("6-15 (Warm)", 6, 15),
        ("16-30 (Hot)", 16, 30),
        ("31+ (Highly Qualified)", 31, 999999),
    ]
    items: list[LeadScoreDistributionItem] = []
    for label, min_val, max_val in ranges:
        cnt = db.execute(
            select(func.count(Lead.id)).where(
                Lead.lead_score >= min_val, Lead.lead_score <= max_val
            )
        ).scalar_one() or 0
        items.append(LeadScoreDistributionItem(score_range=label, count=cnt))

    return SuccessResponse(message="Lead score distribution fetched successfully", data=items)


# ── Conversion Funnel ─────────────────────────────────────────────────

@router.get(
    "/funnel",
    response_model=SuccessResponse[list[FunnelStageItem]],
    summary="Conversion funnel analytics",
    description="Drop-off across 4 stages: All Visitors → Package Viewers → Intent → Converted.",
)
def get_conversion_funnel(
    date_filter: DateFilterLiteral = Query("30d"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    start, end = _date_range(date_filter)

    v1 = db.execute(
        select(func.count(Visitor.id)).where(Visitor.first_seen >= start, Visitor.first_seen <= end)
    ).scalar_one() or 0

    v2 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= start, VisitorEvent.created_at <= end,
            VisitorEvent.event_name.in_(["tour_package_view", "tour_variant_view"]),
        )
    ).scalar_one() or 0

    v3 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= start, VisitorEvent.created_at <= end,
            VisitorEvent.event_name.in_(["enquiry_form_open", "enquiry_form_fill", "whatsapp_click"]),
        )
    ).scalar_one() or 0

    v4 = db.execute(
        select(func.count(func.distinct(VisitorEvent.visitor_id))).where(
            VisitorEvent.created_at >= start, VisitorEvent.created_at <= end,
            VisitorEvent.event_name.in_(["enquiry_submit", "booking_enquiry", "custom_tour_request"]),
        )
    ).scalar_one() or 0

    base = max(1, v1)
    items = [
        FunnelStageItem(stage="1. Total Visitors", visitor_count=v1, conversion_rate=100.0),
        FunnelStageItem(stage="2. Package Viewers", visitor_count=v2, conversion_rate=round((v2 / base) * 100, 1)),
        FunnelStageItem(stage="3. Form / Intent Initiated", visitor_count=v3, conversion_rate=round((v3 / base) * 100, 1)),
        FunnelStageItem(stage="4. Enquiry Submitted", visitor_count=v4, conversion_rate=round((v4 / base) * 100, 1)),
    ]

    return SuccessResponse(message="Conversion funnel fetched successfully", data=items)


# ── Dashboard ─────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=SuccessResponse[SuperAdminDashboardResponse],
    summary="Super-Admin Business Dashboard Overview",
)
def get_super_admin_dashboard(
    current_user: Account = Depends(get_current_admin_or_staff),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    dashboard_data = service.get_super_admin_dashboard()
    return SuccessResponse(message="Dashboard overview fetched successfully", data=dashboard_data)


# ── Data Cleanup (admin-triggered) ────────────────────────────────────

@router.post(
    "/cleanup",
    response_model=SuccessResponse[dict],
    summary="Manually trigger 90-day data retention cleanup",
    description="Delete visitor events, sessions, and visitors older than 90 days. This runs automatically daily but can be triggered manually.",
)
def trigger_cleanup(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    summary = cleanup_old_data(db)
    return SuccessResponse(message="Cleanup completed successfully", data=summary)
