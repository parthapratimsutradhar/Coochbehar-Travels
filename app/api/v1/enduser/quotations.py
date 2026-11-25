import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import QuotationAcceptRequest
from app.schemas.quotation import QuotationRejectRequest, QuotationResponse
from app.schemas.response import ActionResponse, SuccessResponse, documented_error_response
from app.services.enquiry_service import EnquiryService
from app.services.quotation_service import QuotationService

router = APIRouter(
    prefix="/quotations",
    tags=["Quotations"],
)

AUTH_REQUIRED = documented_error_response(
    description="Missing, invalid, or expired authentication token.",
    code="UNAUTHORIZED",
    message="Authentication is required.",
)
QUOTATION_FORBIDDEN = documented_error_response(
    description="The quotation belongs to a different customer.",
    code="FORBIDDEN",
    message="You can only manage your own quotation.",
)
INVALID_REQUEST = documented_error_response(
    description="One or more request fields failed validation.",
    code="VALIDATION_ERROR",
    message="Validation failed.",
    details=[{"field": "field_name", "message": "A valid value is required."}],
)


@router.get(
    "/enquiry/{enquiry_id}",
    response_model=SuccessResponse[list[QuotationResponse]],
    responses={
        401: AUTH_REQUIRED,
        404: documented_error_response(
            description="The enquiry does not exist or is not owned by the authenticated customer.",
            code="NOT_FOUND",
            message="Enquiry not found.",
        ),
    },
    summary="List quotations for my enquiry",
    description=(
        "Returns every quotation version for an enquiry owned by the authenticated customer, "
        "ordered by the service's current quotation order. Hotel and vehicle details are optional, "
        "including for sent quotations; the corresponding arrays are empty when no details exist. "
        "Returns 404 when the enquiry does not exist or belongs to another customer."
    ),
)
def list_enquiry_quotations(
    enquiry_id: Annotated[uuid.UUID, Path(description="UUID of the customer's enquiry.")],
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
    responses={
        401: AUTH_REQUIRED,
        403: QUOTATION_FORBIDDEN,
        404: documented_error_response(
            description="No quotation exists with the supplied ID.",
            code="NOT_FOUND",
            message="Quotation not found.",
        ),
        409: documented_error_response(
            description="Only a sent or viewed quotation can be accepted.",
            code="CONFLICT",
            message="Only a sent quotation can be accepted.",
        ),
        422: INVALID_REQUEST,
    },
    summary="Accept my quotation and provide traveller details",
    description=(
        "Accepts a sent or viewed quotation owned by the authenticated customer and creates "
        "the corresponding booking with the supplied traveller details. Only the quotation "
        "owner may accept it. Between 1 and 50 travellers are required."
    ),
)
def accept_quotation(
    quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation to accept.")],
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
    responses={
        401: AUTH_REQUIRED,
        403: QUOTATION_FORBIDDEN,
        404: documented_error_response(
            description="No quotation exists with the supplied ID.",
            code="NOT_FOUND",
            message="Quotation not found.",
        ),
        409: documented_error_response(
            description="An accepted, rejected, or cancelled quotation cannot be rejected again.",
            code="CONFLICT",
            message="This quotation can no longer be rejected.",
        ),
        422: INVALID_REQUEST,
    },
    summary="Reject my quotation",
    description=(
        "Rejects a quotation owned by the authenticated customer and records the supplied "
        "reason. A quotation that is already accepted, rejected, or cancelled cannot be rejected."
    ),
)
def reject_quotation(
    quotation_id: Annotated[uuid.UUID, Path(description="UUID of the quotation to reject.")],
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


