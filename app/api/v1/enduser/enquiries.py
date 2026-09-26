from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.core.messages.success import EnquirySuccess
from app.models.account import Account
from app.schemas.enquiry import CustomerEnquiryResponse, EnquiryCreate, EnquiryResponse
from app.schemas.response import SuccessResponse
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

