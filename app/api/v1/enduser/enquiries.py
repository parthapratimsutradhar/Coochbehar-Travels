import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.core.messages.success import EnquirySuccess
from app.models.account import Account
from app.schemas.enquiry import (
    CustomerEnquiryResponse,
    CustomerEnquiryUpdate,
    EnquiryCreate,
    EnquiryResponse,
)
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.enquiry_service import EnquiryService

router = APIRouter(
    prefix="/enquiries",
    tags=["Enquiries"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[CustomerEnquiryResponse]],
    summary="List my enquiries",
)
def list_my_enquiries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[list[CustomerEnquiryResponse]]:
    enquiries = EnquiryService(db).list_my_enquiries(
        current_customer.id,
        skip=skip,
        limit=limit,
    )
    return SuccessResponse(
        message=EnquirySuccess.RETRIEVED,
        data=[CustomerEnquiryResponse.model_validate(enquiry) for enquiry in enquiries],
    )


@router.post(
    "",
    response_model=SuccessResponse[EnquiryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit an enquiry",
)
async def create_enquiry(
    payload: EnquiryCreate,
    db: Session = Depends(get_db),
) -> SuccessResponse[EnquiryResponse]:
    enquiry = await EnquiryService(db).create_fixed_tour_enquiry(payload, create_lead=False)
    return SuccessResponse(
        message=EnquirySuccess.CREATED,
        data=EnquiryResponse.model_validate(enquiry),
    )


@router.patch(
    "/{enquiry_id}",
    response_model=SuccessResponse[CustomerEnquiryResponse],
    summary="Update my enquiry",
)
def update_my_enquiry(
    enquiry_id: uuid.UUID,
    payload: CustomerEnquiryUpdate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[CustomerEnquiryResponse]:
    enquiry = EnquiryService(db).update_customer_enquiry(
        enquiry_id,
        current_customer.id,
        payload,
    )
    return SuccessResponse(
        message=EnquirySuccess.UPDATED,
        data=CustomerEnquiryResponse.model_validate(enquiry),
    )


@router.delete(
    "/{enquiry_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Delete my enquiry",
)
def delete_my_enquiry(
    enquiry_id: uuid.UUID,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    EnquiryService(db).delete_customer_enquiry(enquiry_id, current_customer.id)
    return ActionResponse(message=EnquirySuccess.DELETED)

