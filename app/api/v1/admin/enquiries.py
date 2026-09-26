import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import EnquiryStatus
from app.core.messages.success import EnquirySuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse, EnquiryUpdate
from app.schemas.lead import LeadResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, SuccessResponse
from app.services.enquiry_service import EnquiryService
from app.services.lead_service import LeadService

router = APIRouter(
    prefix="/admin/enquiries",
    tags=["Admin - Enquiries"],
)


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an enquiry and sales lead (Admin)",
)
async def create_enquiry(
    payload: EnquiryCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    await EnquiryService(db).create_fixed_tour_enquiry(payload)
    return ActionResponse(message=EnquirySuccess.CREATED)


@router.get(
    "",
    response_model=PaginatedResponse[EnquiryResponse],
    summary="List enquiries (Admin)",
    description="Retrieve all incoming enquiries with optional filtering by status and type.",
)
def list_enquiries(
    status_filter: EnquiryStatus | None = Query(None, alias="status", description="Filter by enquiry status"),
    search: str | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = EnquiryService(db)
    result = service.list_all_enquiries(
        page=page,
        page_size=page_size,
        status=status_filter,
        search=search,
        customer_id=customer_id,
    )
    return PaginatedResponse(
        message=EnquirySuccess.RETRIEVED,
        data=[EnquiryResponse.model_validate(e) for e in result["items"]],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )


@router.get(
    "/{enquiry_id}/lead",
    response_model=SuccessResponse[LeadResponse],
    summary="Get an enquiry lead with activities",
)
def get_enquiry_lead(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    lead = LeadService(db).get_lead_for_enquiry(enquiry_id)
    return SuccessResponse(
        message=EnquirySuccess.LEAD_RETRIEVED,
        data=LeadResponse.model_validate(lead),
    )


@router.patch(
    "/{enquiry_id}",
    response_model=ActionResponse,
    summary="Update enquiry (Admin)",
)
def update_enquiry(
    enquiry_id: uuid.UUID,
    payload: EnquiryUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    EnquiryService(db).update_enquiry(enquiry_id, payload)
    return ActionResponse(message=EnquirySuccess.UPDATED)
