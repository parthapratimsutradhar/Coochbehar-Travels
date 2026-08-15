import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import EnquiryType, LeadSource, LeadStatus
from app.db.database import get_db
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.schemas.custom_tour_request import (
    CustomTourRequestCreate,
    CustomTourRequestResponse,
)
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse

router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
)


@router.post(
    "",
    response_model=EnquiryResponse,
    status_code=status.HTTP_201_CREATED,
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
        enquiry_type=payload.enquiry_type,
        channel=payload.channel,
        package_id=payload.package_id,
        variant_id=payload.variant_id,
        subject=payload.subject,
        message=payload.message,
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
        full_name=payload.subject or f"Enquiry Lead {enquiry_code}",
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        notes=payload.message,
    )
    db.add(lead)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.post(
    "/custom",
    response_model=CustomTourRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a custom tour request",
    description="Submit a custom tour request with group size, vehicle, and hotel requirements.",
)
def create_custom_tour_request(
    payload: CustomTourRequestCreate,
    db: Session = Depends(get_db),
):
    request_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

    # First ensure or create an associated Enquiry if enquiry_id is not provided
    enquiry_id = payload.enquiry_id
    if not enquiry_id:
        enquiry_code = f"ENQ-{uuid.uuid4().hex[:8].upper()}"
        enquiry = Enquiry(
            enquiry_code=enquiry_code,
            visitor_id=payload.visitor_id,
            customer_id=payload.customer_id,
            enquiry_type=EnquiryType.CUSTOM_TOUR,
            channel=EnquiryChannel.WEBSITE,
            subject=f"Custom Tour to {payload.destination}",
            message=payload.special_requirements,
        )
        db.add(enquiry)
        db.flush()
        enquiry_id = enquiry.id

        # Also generate Lead
        lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
        lead = Lead(
            lead_code=lead_code,
            enquiry_id=enquiry_id,
            customer_id=payload.customer_id,
            visitor_id=payload.visitor_id,
            full_name=payload.name,
            mobile=payload.mobile,
            status=LeadStatus.NEW,
            source=LeadSource.WEBSITE,
            notes=f"Custom tour request for {payload.destination} ({payload.pax_no} pax, {payload.no_room} rooms)",
        )
        db.add(lead)

    custom_request = CustomTourRequest(
        request_code=request_code,
        enquiry_id=enquiry_id,
        visitor_id=payload.visitor_id,
        customer_id=payload.customer_id,
        name=payload.name,
        mobile=payload.mobile,
        destination=payload.destination,
        travel_date=payload.travel_date,
        travel_duration=payload.travel_duration,
        pax_no=payload.pax_no,
        no_room=payload.no_room,
        vehicle_type=payload.vehicle_type,
        meal_plan=payload.meal_plan,
        special_requirements=payload.special_requirements,
    )
    db.add(custom_request)
    db.commit()
    db.refresh(custom_request)
    return custom_request
