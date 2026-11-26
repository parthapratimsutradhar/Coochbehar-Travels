from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import QuotationSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import QuotationAcceptRequest
from app.schemas.quotation import CustomerQuotationResponse, QuotationRejectRequest
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
    "/enquiry/{enquiry_code}",
    response_model=SuccessResponse[list[CustomerQuotationResponse]],
    responses={
        401: AUTH_REQUIRED,
        404: documented_error_response(
            description="The enquiry code does not exist or is not owned by the authenticated customer.",
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
    enquiry_code: Annotated[str, Path(min_length=1, max_length=20, description="Enquiry code.")],
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[list[CustomerQuotationResponse]]:
    enquiry = EnquiryService(db).get_enquiry_by_code(enquiry_code)
    if enquiry.customer_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found.")

    quotations = QuotationService(db).list_enquiry_quotations(enquiry.id)
    return SuccessResponse(
        message=QuotationSuccess.RETRIEVED,
        data=[CustomerQuotationResponse.model_validate(quotation) for quotation in quotations],
    )


@router.get(
    "/{quotation_code}",
    response_model=SuccessResponse[CustomerQuotationResponse],
    responses={
        401: AUTH_REQUIRED,
        404: documented_error_response(
            description="The quotation does not exist or is not owned by the authenticated customer.",
            code="NOT_FOUND",
            message="Quotation not found.",
        ),
    },
    summary="Get my quotation by quotation code",
    description=(
        "Returns a quotation owned by the authenticated customer, addressed by its quotation "
        "code. Opening a sent quotation changes its status to `VIEWED`; an expired quotation "
        "is returned as `EXPIRED`."
    ),
)
def get_customer_quotation(
    quotation_code: Annotated[str, Path(min_length=1, max_length=50, description="Quotation code.")],
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[CustomerQuotationResponse]:
    service = QuotationService(db)
    quotation = service.get_quotation_by_code(quotation_code)
    if quotation.customer_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")

    quotation = service.mark_quotation_viewed(quotation)
    return SuccessResponse(
        message=QuotationSuccess.RETRIEVED,
        data=CustomerQuotationResponse.model_validate(quotation),
    )


@router.post(
    "/{quotation_code}/accept",
    response_model=ActionResponse,
    responses={
        401: AUTH_REQUIRED,
        403: QUOTATION_FORBIDDEN,
        404: documented_error_response(
            description="No quotation exists with the supplied code.",
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
    quotation_code: Annotated[str, Path(min_length=1, max_length=50, description="Quotation code.")],
    payload: QuotationAcceptRequest,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    quotation = QuotationService(db).get_quotation_by_reference(quotation_code)
    QuotationService(db).accept_quotation(
        quotation_id=quotation.id,
        customer=current_customer,
        travellers=[traveller.model_dump() for traveller in payload.travellers],
    )
    return ActionResponse(message=QuotationSuccess.ACCEPTED)


@router.post(
    "/{quotation_code}/reject",
    response_model=ActionResponse,
    responses={
        401: AUTH_REQUIRED,
        403: QUOTATION_FORBIDDEN,
        404: documented_error_response(
            description="No quotation exists with the supplied code.",
            code="NOT_FOUND",
            message="Quotation not found.",
        ),
        409: documented_error_response(
            description="Only a sent or viewed quotation can be rejected.",
            code="CONFLICT",
            message="This quotation can no longer be rejected.",
        ),
        422: INVALID_REQUEST,
    },
    summary="Reject my quotation",
    description=(
        "Rejects a quotation owned by the authenticated customer and records the supplied "
        "reason. Only sent or viewed quotations can be rejected."
    ),
)
def reject_quotation(
    quotation_code: Annotated[str, Path(min_length=1, max_length=50, description="Quotation code.")],
    payload: QuotationRejectRequest,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    quotation = QuotationService(db).get_quotation_by_reference(quotation_code)
    QuotationService(db).reject_quotation(
        quotation_id=quotation.id,
        customer=current_customer,
        reason=payload.reason,
    )
    return ActionResponse(message=QuotationSuccess.REJECTED)


