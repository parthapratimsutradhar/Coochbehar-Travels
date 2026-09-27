import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import QuotationAcceptRequest
from app.schemas.quotation import QuotationRejectRequest, QuotationResponse
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


@router.post(
    "/{quotation_id}/accept",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Accept my quotation and provide traveller details",
)
def accept_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationAcceptRequest,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    QuotationService(db).accept_quotation(
        quotation_id=quotation_id,
        customer=current_customer,
        travellers=[traveller.model_dump() for traveller in payload.travellers],
    )
    return ActionResponse(message=QuotationSuccess.ACCEPTED)


@router.post(
    "/{quotation_id}/reject",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Reject my quotation",
)
def reject_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationRejectRequest,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    QuotationService(db).reject_quotation(
        quotation_id=quotation_id,
        customer=current_customer,
        reason=payload.reason,
    )
    return ActionResponse(message=QuotationSuccess.REJECTED)


