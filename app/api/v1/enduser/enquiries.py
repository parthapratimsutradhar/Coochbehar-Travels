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
from app.schemas.custom_tour_request import CustomTourRequestCreate
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse

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
def create_enquiry(
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

    # Automatically create sales Lead from enquiry
    lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
    lead = Lead(
        lead_code=lead_code,
        enquiry_id=enquiry.id,
        customer_id=payload.customer_id,
        visitor_id=payload.visitor_id,
        full_name=payload.name or payload.subject or f"Enquiry Lead {enquiry_code}",
        mobile=payload.mobile,
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        notes=payload.message,
    )
    db.add(lead)
    db.commit()
    return ActionResponse(message="Enquiry submitted successfully")


@router.post(
    "/custom",
    response_model=ActionResponse,
    responses={422: {"model": ErrorResponse}},
    status_code=status.HTTP_201_CREATED,
    summary="Submit a custom tour request",
    description="Submit a custom tour request with group size, vehicle, and hotel requirements.",
)
def create_custom_tour_request(
    payload: CustomTourRequestCreate,
    db: Session = Depends(get_db),
):
    enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"
    enquiry = Enquiry(
        enquiry_code=enquiry_code,
        visitor_id=payload.visitor_id,
        customer_id=payload.customer_id,
        enquiry_type=EnquiryType.enquiry_type,
        channel=payload.channel,
        subject=f"Custom Tour to {payload.destination}",
        message=payload.special_requirements,
        enquirer_name=payload.name,
        enquirer_phone=payload.mobile,
        destination=payload.destination,
        travel_date=payload.travel_date,
        travel_duration=payload.travel_duration,
        pax_no=payload.pax_no,
        no_room=payload.no_room,
        vehicle_type=payload.vehicle_type,
        meal_plan=payload.meal_plan,
        special_requirements=payload.special_requirements,
    )
    db.add(enquiry)
    db.flush()

    # Also generate Lead
    lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
    lead = Lead(
        lead_code=lead_code,
        enquiry_id=enquiry.id,
        customer_id=payload.customer_id,
        visitor_id=payload.visitor_id,
        full_name=enquiry.enquirer_name,
        mobile=enquiry.enquirer_phone,
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        notes=f"Custom tour request for {payload.destination} ({payload.pax_no} pax, {payload.no_room} rooms)",
    )
    db.add(lead)
    db.commit()
    return ActionResponse(message="Custom tour request submitted successfully")
