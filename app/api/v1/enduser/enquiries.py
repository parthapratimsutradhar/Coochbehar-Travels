import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_customer
from app.db.database import get_db
from app.models.account import Account
from app.models.lead import Lead
from app.schemas.custom_tour_request import CustomTourRequestCreate
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.enquiry_service import EnquiryService
from app.services.socket_service import emit_enquiry_created, emit_lead_created

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
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = EnquiryService(db)
    enquiries = service.list_my_enquiries(current_customer.id, skip=skip, limit=limit)
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
    service = EnquiryService(db)
    enquiry = await service.create_fixed_tour_enquiry(payload)
    lead = db.scalar(select(Lead).where(Lead.enquiry_id == enquiry.id))
    if lead:
        emit_lead_created(lead)
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
    service = EnquiryService(db)
    enquiry = await service.create_custom_tour_enquiry(payload)
    lead = db.scalar(select(Lead).where(Lead.enquiry_id == enquiry.id))
    if lead:
        emit_lead_created(lead)
    return ActionResponse(message="Custom tour request submitted successfully")

