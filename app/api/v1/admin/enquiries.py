import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import EnquiryStatus, EnquiryType
from app.db.database import get_db
from app.models.enquiry import Enquiry
from app.schemas.enquiry import EnquiryResponse, EnquiryUpdate
from app.schemas.response import SuccessResponse

router = APIRouter(
    prefix="/admin/enquiries",
    tags=["Admin - Enquiries"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[EnquiryResponse]],
    summary="List enquiries (Admin)",
    description="Retrieve all incoming enquiries with optional filtering by status and type.",
)
def list_enquiries(
    status: EnquiryStatus | None = Query(None, description="Filter by enquiry status"),
    enquiry_type: EnquiryType | None = Query(None, description="Filter by enquiry type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Enquiry).order_by(Enquiry.created_at.desc())

    if status:
        stmt = stmt.where(Enquiry.status == status)
    if enquiry_type:
        stmt = stmt.where(Enquiry.enquiry_type == enquiry_type)

    stmt = stmt.offset(skip).limit(limit)
    enquiries = db.execute(stmt).scalars().all()
    return SuccessResponse(
        message="Enquiries fetched successfully",
        data=[EnquiryResponse.model_validate(e) for e in enquiries],
    )


@router.get(
    "/{enquiry_id}",
    response_model=SuccessResponse[EnquiryResponse],
    summary="Get single enquiry detail",
)
def get_enquiry(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    stmt = select(Enquiry).where(Enquiry.id == enquiry_id)
    enquiry = db.execute(stmt).scalar_one_or_none()
    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enquiry with ID {enquiry_id} not found",
        )
    return SuccessResponse(
        message="Enquiry fetched successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )


@router.patch(
    "/{enquiry_id}",
    response_model=SuccessResponse[EnquiryResponse],
    summary="Update enquiry status (Admin)",
)
def update_enquiry(
    enquiry_id: uuid.UUID,
    payload: EnquiryUpdate,
    db: Session = Depends(get_db),
):
    stmt = select(Enquiry).where(Enquiry.id == enquiry_id)
    enquiry = db.execute(stmt).scalar_one_or_none()
    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enquiry with ID {enquiry_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(enquiry, field, value)

    db.commit()
    db.refresh(enquiry)
    return SuccessResponse(
        message="Enquiry updated successfully",
        data=EnquiryResponse.model_validate(enquiry),
    )

