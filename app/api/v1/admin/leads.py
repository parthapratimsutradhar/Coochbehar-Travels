import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import LeadSource, LeadStatus
from app.core.messages.error import LeadError
from app.core.messages.success import LeadSuccess
from app.db.database import get_db
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.schemas.lead import (
    LeadActivityCreate,
    LeadActivityResponse,
    LeadCreate,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.response import SuccessResponse
from app.services.lead_scoring_service import LeadScoringService
from app.services.socket_service import (
    emit_lead_activity_created,
    emit_lead_created,
    emit_lead_score_updated,
    emit_lead_status_updated,
)

router = APIRouter(
    prefix="/admin/leads",
    tags=["Admin - Sales Leads Pipeline"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[LeadResponse]],
    summary="List sales leads",
    description="Retrieve sales leads with status, source, and search filters.",
)
def list_leads(
    status: LeadStatus | None = Query(None, description="Filter by lead status"),
    source: LeadSource | None = Query(None, description="Filter by lead source"),
    search: str | None = Query(None, description="Search by name, email, or mobile"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Lead).options(selectinload(Lead.activities)).order_by(Lead.created_at.desc())

    if status:
        stmt = stmt.where(Lead.status == status)
    if source:
        stmt = stmt.where(Lead.source == source)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (Lead.full_name.ilike(search_pattern))
            | (Lead.email.ilike(search_pattern))
            | (Lead.mobile.ilike(search_pattern))
        )

    stmt = stmt.offset(skip).limit(limit)
    leads = db.execute(stmt).scalars().all()
    return SuccessResponse(
        message=LeadSuccess.RETRIEVED,
        data=[LeadResponse.model_validate(l) for l in leads],
    )


@router.get(
    "/{lead_id}",
    response_model=SuccessResponse[LeadResponse],
    summary="Get single sales lead detail",
)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    stmt = select(Lead).options(selectinload(Lead.activities)).where(Lead.id == lead_id)
    lead = db.execute(stmt).scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=LeadError.LEAD_NOT_FOUND,
        )
    return SuccessResponse(
        message=LeadSuccess.RETRIEVED,
        data=LeadResponse.model_validate(lead),
    )


@router.post(
    "",
    response_model=SuccessResponse[LeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a new lead",
)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
):
    lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
    lead_score = max(0, min(100, payload.lead_score))
    lead = Lead(
        lead_code=lead_code,
        enquiry_id=payload.enquiry_id,
        customer_id=payload.customer_id,
        visitor_id=payload.visitor_id,
        full_name=payload.full_name,
        mobile=payload.mobile,
        email=payload.email,
        whatsapp_opt_in=payload.whatsapp_opt_in,
        lead_score=lead_score,
        status=payload.status,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(lead)
    db.commit()

    stmt = select(Lead).options(selectinload(Lead.activities)).where(Lead.id == lead.id)
    created = db.execute(stmt).scalar_one()

    # Emit real-time Socket.IO event to admin dashboard
    emit_lead_created(created)

    return SuccessResponse(
        message=LeadSuccess.CREATED,
        data=LeadResponse.model_validate(created),
    )


@router.patch(
    "/{lead_id}",
    response_model=SuccessResponse[LeadResponse],
    summary="Update sales lead status / notes",
)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
):
    stmt = select(Lead).options(selectinload(Lead.activities)).where(Lead.id == lead_id)
    lead = db.execute(stmt).scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=LeadError.LEAD_NOT_FOUND,
        )

    prev_status = lead.status
    prev_score = lead.lead_score

    update_data = payload.model_dump(exclude_unset=True)
    if "lead_score" in update_data and update_data["lead_score"] is not None:
        update_data["lead_score"] = max(0, min(100, update_data["lead_score"]))

    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    # Emit real-time Socket.IO events for status or score changes
    if "status" in update_data and lead.status != prev_status:
        emit_lead_status_updated(
            lead,
            previous_status=prev_status.value if hasattr(prev_status, "value") else str(prev_status),
            new_status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        )

    if "lead_score" in update_data and lead.lead_score != prev_score:
        emit_lead_score_updated(
            lead,
            previous_score=prev_score,
            new_score=lead.lead_score,
            delta=lead.lead_score - prev_score,
            reason="ADMIN_MANUAL_UPDATE",
        )

    return SuccessResponse(
        message=LeadSuccess.UPDATED,
        data=LeadResponse.model_validate(lead),
    )


@router.post(
    "/{lead_id}/activities",
    response_model=SuccessResponse[LeadActivityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Log sales activity / follow-up for a lead",
    description="Record WhatsApp messages, phone calls, emails, and schedule next follow-up dates.",
)
def log_lead_activity(
    lead_id: uuid.UUID,
    payload: LeadActivityCreate,
    db: Session = Depends(get_db),
):
    stmt = select(Lead).where(Lead.id == lead_id)
    lead = db.execute(stmt).scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=LeadError.LEAD_NOT_FOUND,
        )

    activity = LeadActivity(
        lead_id=lead_id,
        user_id=payload.user_id,
        channel=payload.channel,
        activity_type=payload.activity_type,
        notes=payload.notes,
        next_follow_up_at=payload.next_follow_up_at,
    )
    db.add(activity)

    # Update lead last_contacted_at
    lead.last_contacted_at = datetime.now()

    # Dynamic scoring for staff activity
    scoring_service = LeadScoringService(db)
    delta = scoring_service.calculate_activity_score(activity)
    prev_score, new_score, actual_delta = scoring_service.apply_score_change(
        lead, delta, reason=activity.activity_type
    )

    db.commit()
    db.refresh(activity)
    db.refresh(lead)

    # Emit real-time Socket.IO events to admin dashboard
    emit_lead_activity_created(lead, activity)
    if actual_delta > 0:
        emit_lead_score_updated(
            lead,
            previous_score=prev_score,
            new_score=new_score,
            delta=actual_delta,
            reason=f"ACTIVITY_{activity.activity_type.upper()}",
        )

    return SuccessResponse(
        message="Lead activity logged successfully",
        data=LeadActivityResponse.model_validate(activity),
    )
