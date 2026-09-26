import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.quotation import QuotationResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.enquiry_service import EnquiryService
from app.services.quotation_service import QuotationService

router = APIRouter(
    prefix="/quotations",
    tags=["Quotations"],
)


@router.get(
    "/enquiry/{enquiry_id}",
    response_model=SuccessResponse[list[QuotationResponse]],
    responses={404: {"model": ErrorResponse}},
    summary="List quotations for my enquiry",
)
def list_enquiry_quotations(
    enquiry_id: uuid.UUID,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[list[QuotationResponse]]:
    enquiry = EnquiryService(db).get_enquiry(enquiry_id)
    if enquiry.customer_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found.")

    quotations = QuotationService(db).list_enquiry_quotations(enquiry_id)
    return SuccessResponse(
        message=QuotationSuccess.RETRIEVED,
        data=[QuotationResponse.model_validate(quotation) for quotation in quotations],
    )


