import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import BookingSource, BookingStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import (
    BookingCostCreate,
    BookingCostResponse,
    BookingDetailResponse,
    BookingResponse,
    BookingStatusUpdate,
    BookingTravelerCreate,
    BookingTravelerResponse,
    OfflineBookingCreate,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.payment import BookingPaymentCreate, BookingPaymentResponse
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService

router = APIRouter(
    prefix="/admin/bookings",
    tags=["Admin - Bookings"],
)


@router.post(
    "/offline",
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
    summary="Create an offline booking (walk-in / phone)",
)
def create_offline_booking(
    payload: OfflineBookingCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    booking = service.create_offline_booking(payload, staff_user=current_user)
    return SuccessResponse(
        message="Offline booking created successfully",
        data=BookingResponse.model_validate(booking),
    )


@router.get(
    "",
    response_model=PaginatedResponse[BookingResponse],
    summary="List all bookings (Admin)",
)
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: BookingStatus | None = Query(None, alias="status"),
    source: BookingSource | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    result = service.list_all_bookings(
        page=page, page_size=page_size, status=status_filter, source=source, search=search,
    )
    return PaginatedResponse(
        message="Bookings fetched successfully",
        data=[BookingResponse.model_validate(b) for b in result["items"]],
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
    "/{booking_id}",
    response_model=SuccessResponse[BookingDetailResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Get booking detail with travellers, costs, and status history",
)
def get_booking_detail(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    detail = service.get_booking_detail(booking_id)
    return SuccessResponse(
        message="Booking detail fetched successfully",
        data=detail,
    )


@router.patch(
    "/{booking_id}/status",
    response_model=ActionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Update booking status",
)
def update_booking_status(
    booking_id: uuid.UUID,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    service.update_booking_status(booking_id, payload.status, reason=payload.reason)
    return ActionResponse(message="Booking status updated successfully")


@router.post(
    "/{booking_id}/costs",
    response_model=SuccessResponse[BookingCostResponse],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
    summary="Add a cost line to a booking",
)
def add_booking_cost(
    booking_id: uuid.UUID,
    payload: BookingCostCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    cost = service.add_booking_cost(booking_id, payload)
    return SuccessResponse(
        message="Booking cost added successfully",
        data=BookingCostResponse.model_validate(cost),
    )


@router.post(
    "/{booking_id}/travellers",
    response_model=SuccessResponse[BookingTravelerResponse],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
    summary="Add a traveller to a booking",
)
def add_traveller(
    booking_id: uuid.UUID,
    payload: BookingTravelerCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = BookingService(db)
    traveller = service.add_traveller(booking_id, payload)
    return SuccessResponse(
        message="Traveller added successfully",
        data=BookingTravelerResponse.model_validate(traveller),
    )


@router.post(
    "/{booking_id}/payments",
    response_model=SuccessResponse[BookingPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
    summary="Record a payment against a booking",
)
def record_booking_payment(
    booking_id: uuid.UUID,
    payload: BookingPaymentCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    # Override booking_id from URL path
    payload.booking_id = booking_id
    service = PaymentService(db)
    payment = service.record_payment(payload, recorded_by=current_user)
    return SuccessResponse(
        message="Payment recorded successfully",
        data=BookingPaymentResponse.model_validate(payment),
    )


@router.get(
    "/{booking_id}/payments",
    response_model=SuccessResponse[list[BookingPaymentResponse]],
    responses={404: {"model": ErrorResponse}},
    summary="List payments for a booking",
)
def list_booking_payments(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
):
    service = PaymentService(db)
    payments = service.list_booking_payments(booking_id)
    return SuccessResponse(
        message="Booking payments fetched successfully",
        data=[BookingPaymentResponse.model_validate(p) for p in payments],
    )
