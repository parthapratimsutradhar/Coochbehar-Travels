import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.models.account import Account
from app.schemas.quotation import QuotationResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.quotation_service import QuotationService

router = APIRouter(
    prefix="/quotations",
    tags=["Quotations"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[QuotationResponse]],
    responses={401: {"model": ErrorResponse}},
    summary="List my quotations",
    description="Retrieve quotations linked to the authenticated customer.",
)
def list_my_quotations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_customer: Account = Depends(get_current_customer),
):
    service = QuotationService(db)
    quotations = service.list_customer_quotations(current_customer.id, skip=skip, limit=limit)
    return SuccessResponse(
        message="Your quotations fetched successfully",
        data=[QuotationResponse.model_validate(q) for q in quotations],
    )


@router.get(
    "/{quotation_id}",
    response_model=SuccessResponse[QuotationResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get quotation detail",
)
def get_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_customer: Account = Depends(get_current_customer),
):
    service = QuotationService(db)
    quotation = service.get_quotation(quotation_id)
    return SuccessResponse(
        message="Quotation fetched successfully",
        data=QuotationResponse.model_validate(quotation),
    )


@router.post(
    "/{quotation_id}/accept",
    response_model=ActionResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Accept a quotation",
)
def accept_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_customer: Account = Depends(get_current_customer),
):
    service = QuotationService(db)
    service.accept_quotation(quotation_id, customer=current_customer)
    return ActionResponse(message="Quotation accepted successfully")


@router.post(
    "/{quotation_id}/reject",
    response_model=ActionResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Reject a quotation",
)
def reject_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_customer: Account = Depends(get_current_customer),
):
    service = QuotationService(db)
    service.reject_quotation(quotation_id, customer=current_customer)
    return ActionResponse(message="Quotation rejected successfully")
