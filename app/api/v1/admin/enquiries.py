import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import EnquiryStatus, EnquiryType
from app.db.database import get_db
from app.models.account import Account
from app.schemas.enquiry import EnquiryResponse, EnquiryUpdate
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import SuccessResponse
from app.services.enquiry_service import EnquiryService
from app.services.socket_service import (
    emit_enquiry_status_updated,
    emit_enquiry_updated,
)

router = APIRouter(
    prefix="/admin/enquiries",
    tags=["Admin - Enquiries"],
)


@router.get(
    "",
    response_model=PaginatedResponse[EnquiryResponse],
    summary="List enquiries (Admin)",
    description="Retrieve all incoming enquiries with optional filtering by status and type.",
)
def list_enquiries(
    status_filter: EnquiryStatus | None = Query(None, alias="status", description="Filter by enquiry status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = EnquiryService(db)
    result = service.list_all_enquiries(page=page, page_size=page_size, status=status_filter, search=search)
    return PaginatedResponse(
        message="Enquiries fetched successfully",
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
    "/{enquiry_id}",
    response_model=SuccessResponse[EnquiryResponse],
    summary="Get single enquiry detail",
)
def get_enquiry(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = EnquiryService(db)
    enquiry = service.get_enquiry(enquiry_id)
    return SuccessResponse(
        message="Enquiry fetched successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )


@router.patch(
    "/{enquiry_id}",
    response_model=SuccessResponse[EnquiryResponse],
    summary="Update enquiry (Admin)",
)
def update_enquiry(
    enquiry_id: uuid.UUID,
    payload: EnquiryUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = EnquiryService(db)
    enquiry = service.get_enquiry(enquiry_id)
    prev_status = enquiry.status

    # Apply field-level updates via repo (through service)
    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        enquiry = service.update_enquiry_status(enquiry_id, update_data.pop("status"))

    # For any remaining fields, apply directly and commit
    if update_data:
        for field, value in update_data.items():
            setattr(enquiry, field, value)
        db.commit()
        db.refresh(enquiry)

    # Emit real-time Socket.IO events for enquiry changes
    emit_enquiry_updated(enquiry)
    if enquiry.status != prev_status:
        emit_enquiry_status_updated(
            enquiry,
            previous_status=prev_status.value if hasattr(prev_status, "value") else str(prev_status),
            new_status=enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status),
        )

    return SuccessResponse(
        message="Enquiry updated successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )
