import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import QuotationStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.quotation import (
    QuotationConvertToBookingRequest,
    QuotationCreate,
    QuotationResponse,
    QuotationUpdate,
)
from app.schemas.tour_offer import TourOfferApplyRequest, TourOfferCalculationResult
from app.schemas.booking import BookingResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.quotation_service import QuotationService
from app.services.tour_offer_service import TourOfferService

router = APIRouter(
    prefix="/admin/quotations",
    tags=["Admin - Quotations"],
)


@router.post(
    "",
    response_model=SuccessResponse[QuotationResponse],
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Create a new quotation",
)
def create_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    quotation = service.create_quotation(payload, staff_user=current_user)
    return SuccessResponse(
        message="Quotation created successfully",
        data=QuotationResponse.model_validate(quotation),
    )


@router.get(
    "",
    response_model=PaginatedResponse[QuotationResponse],
    summary="List all quotations (Admin)",
)
def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: QuotationStatus | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    result = service.list_all_quotations(page=page, page_size=page_size, status=status_filter, search=search)
    return PaginatedResponse(
        message="Quotations fetched successfully",
        data=[QuotationResponse.model_validate(q) for q in result["items"]],
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
    "/{quotation_id}",
    response_model=SuccessResponse[QuotationResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get quotation detail",
)
def get_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    quotation = service.get_quotation(quotation_id)
    return SuccessResponse(
        message="Quotation fetched successfully",
        data=QuotationResponse.model_validate(quotation),
    )


@router.patch(
    "/{quotation_id}",
    response_model=SuccessResponse[QuotationResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Update a quotation",
)
def update_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    quotation = service.update_quotation(quotation_id, payload)
    return SuccessResponse(
        message="Quotation updated successfully",
        data=QuotationResponse.model_validate(quotation),
    )


@router.post(
    "/{quotation_id}/offer",
    response_model=SuccessResponse[TourOfferCalculationResult],
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Apply a tour offer to a quotation",
)
def apply_offer_to_quotation(
    quotation_id: uuid.UUID,
    payload: TourOfferApplyRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    del current_user
    service = QuotationService(db)
    quotation = service.get_quotation(quotation_id)
    offer_service = TourOfferService(db)
    result = offer_service.apply_offer(
        offer_id=payload.offer_id,
        variant_id=quotation.variant_id,
        booking_amount=quotation.subtotal,
        customer_id=quotation.customer_id,
    )
    offer_service.apply_offer_to_quotation(quotation=quotation, offer_id=payload.offer_id)
    return SuccessResponse(message="Offer applied successfully", data=result)


@router.post(
    "/{quotation_id}/send",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Mark quotation as sent",
)
def send_quotation(
    quotation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    service.send_quotation(quotation_id)
    return ActionResponse(message="Quotation marked as sent successfully")


@router.post(
    "/{quotation_id}/convert",
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Convert accepted quotation to a booking",
)
def convert_quotation_to_booking(
    quotation_id: uuid.UUID,
    payload: QuotationConvertToBookingRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    booking = service.convert_quotation_to_booking(
        quotation_id, staff_user=current_user, booking_type=payload.booking_type, notes=payload.notes,
    )
    return SuccessResponse(
        message="Quotation converted to booking successfully",
        data=BookingResponse.model_validate(booking),
    )


@router.get(
    "/enquiry/{enquiry_id}",
    response_model=SuccessResponse[list[QuotationResponse]],
    summary="List quotation versions for an enquiry",
)
def list_enquiry_quotations(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = QuotationService(db)
    quotations = service.list_enquiry_quotations(enquiry_id)
    return SuccessResponse(
        message="Enquiry quotations fetched successfully",
        data=[QuotationResponse.model_validate(q) for q in quotations],
    )
