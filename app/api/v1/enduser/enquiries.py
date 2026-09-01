import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_customer
from app.core.enums import EnquiryType, LeadSource, LeadStatus
from app.db.database import get_db
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.tour_package import TourPackage
from app.schemas.custom_tour_request import CustomTourRequestCreate
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.lead_scoring_service import LeadScoringService
from app.services.notification_service import NotificationService
from app.services.socket_service import emit_lead_created

router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[EnquiryResponse]],
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List the authenticated customer's enquiries",
    description="Retrieve enquiries submitted by the currently authenticated customer, newest first.",
)
def list_my_enquiries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Enquiry)
        .where(Enquiry.customer_id == current_customer.id)
        .order_by(Enquiry.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    enquiries = db.execute(stmt).scalars().all()
    return SuccessResponse(
        message="Your enquiries fetched successfully",
        data=[EnquiryResponse.model_validate(enquiry) for enquiry in enquiries],
    )


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Submit a new enquiry",
    description="Submit an enquiry (Fixed Tour, Custom Tour, or General query). Automatically creates a sales Lead record.",
)
async def create_enquiry(
    payload: EnquiryCreate,
    db: Session = Depends(get_db),
):
    enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"

    enquiry = Enquiry(
        enquiry_code=enquiry_code,
        visitor_id=payload.visitor_id,
        customer_id=payload.customer_id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=payload.channel,
        package_id=payload.package_id,
        variant_id=payload.variant_id,
        subject=payload.subject,
        message=payload.message,
        enquirer_name=payload.name,
        enquirer_phone=payload.mobile,
    )
    db.add(enquiry)
    db.flush()

    # Automatically create sales Lead from enquiry with initial score
    initial_score = LeadScoringService(db).calculate_initial_score(enquiry)
    lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
    lead = Lead(
        lead_code=lead_code,
        enquiry_id=enquiry.id,
        customer_id=payload.customer_id,
        visitor_id=payload.visitor_id,
        full_name=payload.name or payload.subject or f"Enquiry Lead {enquiry_code}",
        mobile=payload.mobile,
        lead_score=initial_score,
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        notes=payload.message,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Emit real-time Socket.IO event to admin dashboard
    emit_lead_created(lead)

    package = db.get(TourPackage, payload.package_id) if payload.package_id else None
    tour_name = package.title if package else (payload.subject or "custom tour enquiry")
    enquiry_date = enquiry.created_at.isoformat() if enquiry.created_at else None
    service = NotificationService(db)
    await service.notify_admins(
        notification_type="ENQUIRY_CREATED",
        title="New customer enquiry",
        message=f"{payload.name or 'A customer'} enquired about {tour_name} on {enquiry_date}.",
        data={
            "customer_id": str(payload.customer_id) if payload.customer_id else None,
            "customer_name": payload.name,
            "tour_name": tour_name,
            "enquiry_id": str(enquiry.id),
            "enquiry_date": enquiry_date,
        },
    )
    if payload.customer_id:
        await service.notify_customer(
            payload.customer_id,
            notification_type="ENQUIRY_CONFIRMED",
            title="Enquiry received",
            message=f"Your enquiry about {tour_name} was received. Our team will follow up with the next steps.",
            data={"tour_name": tour_name, "enquiry_id": str(enquiry.id)},
        )
    return ActionResponse(message="Enquiry submitted successfully")


@router.post(
    "/custom",
    response_model=ActionResponse,
    responses={422: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
    summary="Submit a custom tour request",
    description="Submit a custom tour request with group size, vehicle, and hotel requirements.",
)
async def create_custom_tour_request(
    payload: CustomTourRequestCreate,
    db: Session = Depends(get_db),
):
    enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"
    enquiry = Enquiry(
        enquiry_code=enquiry_code,
        visitor_id=payload.visitor_id,
        customer_id=payload.customer_id,
        enquiry_type=payload.enquiry_type or EnquiryType.CUSTOM_TOUR,
        channel=payload.channel,
        subject=f"Custom Tour to {payload.destination}",
        message=payload.special_requirements,
        enquirer_name=payload.name,
        enquirer_phone=payload.mobile,
        destination=payload.destination,
        travel_date=payload.travel_date,
        travel_duration_day=payload.travel_duration_day,
        travel_duration_night=payload.travel_duration_night,
        pax_no=payload.pax_no,
        no_room=payload.no_room,
        vehicle_type=payload.vehicle_type,
        meal_plan=payload.meal_plan,
        special_requirements=payload.special_requirements,
    )
    db.add(enquiry)
    db.flush()

    # Also generate Lead with initial score
    initial_score = LeadScoringService(db).calculate_initial_score(enquiry)
    lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
    lead = Lead(
        lead_code=lead_code,
        enquiry_id=enquiry.id,
        customer_id=payload.customer_id,
        visitor_id=payload.visitor_id,
        full_name=enquiry.enquirer_name,
        mobile=enquiry.enquirer_phone,
        lead_score=initial_score,
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        notes=f"Custom tour request for {payload.destination} ({payload.pax_no} pax, {payload.no_room} rooms)",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Emit real-time Socket.IO event to admin dashboard
    emit_lead_created(lead)

    enquiry_date = enquiry.created_at.isoformat() if enquiry.created_at else None
    service = NotificationService(db)
    tour_name = f"custom tour to {payload.destination}"
    await service.notify_admins(
        notification_type="ENQUIRY_CREATED",
        title="New custom tour enquiry",
        message=f"{payload.name or 'A customer'} enquired about {tour_name} on {enquiry_date}.",
        data={
            "customer_id": str(payload.customer_id) if payload.customer_id else None,
            "customer_name": payload.name,
            "tour_name": tour_name,
            "enquiry_id": str(enquiry.id),
            "enquiry_date": enquiry_date,
        },
    )
    if payload.customer_id:
        await service.notify_customer(
            payload.customer_id,
            notification_type="ENQUIRY_CONFIRMED",
            title="Enquiry received",
            message=f"Your enquiry about {tour_name} was received. Our team will follow up with the next steps.",
            data={"tour_name": tour_name, "enquiry_id": str(enquiry.id)},
        )
    return ActionResponse(message="Custom tour request submitted successfully")
