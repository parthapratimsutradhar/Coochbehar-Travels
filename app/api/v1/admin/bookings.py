import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_staff
from app.core.enums import BookingSource, BookingStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import (
    BookingDayDetailResponse,
    BookingDetailResponse,
    BookingEmailRequest,
    BookingResponse,
    BookingStatusUpdate,
    BookingTravelerCreate,
    BookingTravelerResponse,
    BookingTravelerUpdate,
    OfflineBookingCreate,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.booking_service import BookingService


router = APIRouter(prefix="/admin/bookings", tags=["Admin - Bookings"])


@router.post(
    "",
    response_model=SuccessResponse[BookingDetailResponse],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
    summary="Create a booking with travellers and trip costs",
)
def create_booking(
    payload: OfflineBookingCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[BookingDetailResponse]:
    service = BookingService(db)
    booking = service.create_offline_booking(payload, current_user)
    return SuccessResponse(
        message="Booking created successfully",
        data=service.get_booking_detail(booking.id),
    )


@router.get(
    "",
    response_model=PaginatedResponse[BookingResponse],
    summary="List all bookings",
)
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: uuid.UUID | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None, ge=2000, le=2200),
    status_filter: BookingStatus | None = Query(None, alias="status"),
    source: BookingSource | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> PaginatedResponse[BookingResponse]:
    del current_user
    result = BookingService(db).list_all_bookings(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        month=month,
        year=year,
        status=status_filter,
        source=source,
        search=search,
    )
    return PaginatedResponse(
        message="Items fetched successfully",
        data=[BookingResponse.model_validate(item) for item in result["items"]],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=page < result["total_pages"],
            has_previous=page > 1,
        ),
    )


@router.get(
    "/day/{travel_day}",
    response_model=SuccessResponse[list[BookingDayDetailResponse]],
    summary="List bookings for a travel day",
)
def list_bookings_for_day(
    travel_day: date,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[list[BookingDayDetailResponse]]:
    del current_user
    bookings = BookingService(db).list_bookings_for_day(travel_day)
    return SuccessResponse(
        message="Bookings for the day fetched successfully",
        data=[BookingDayDetailResponse.model_validate(item) for item in bookings],
    )


@router.get(
    "/{booking_id}/pdf",
    responses={404: {"model": ErrorResponse}},
    summary="Download a booking PDF",
)
def download_booking_pdf(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> Response:
    del current_user
    booking_code, pdf_content = BookingService(db).render_booking_pdf(booking_id)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{booking_code}.pdf"',
        },
    )


@router.post(
    "/{booking_id}/send",
    response_model=ActionResponse,
    summary="Email a booking PDF",
)
async def send_booking_pdf(
    booking_id: uuid.UUID,
    payload: BookingEmailRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    del current_user
    await BookingService(db).email_booking(booking_id, payload.recipient_email)
    return ActionResponse(message="Booking PDF sent successfully")


@router.get(
    "/{booking_id}",
    response_model=SuccessResponse[BookingDetailResponse],
    summary="Get booking details",
)
def get_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[BookingDetailResponse]:
    del current_user
    return SuccessResponse(
        message="Booking details fetched successfully",
        data=BookingService(db).get_booking_detail(booking_id),
    )


@router.patch(
    "/{booking_id}/status",
    response_model=ActionResponse,
    summary="Update booking status",
)
def update_booking_status(
    booking_id: uuid.UUID,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    BookingService(db).update_booking_status(
        booking_id,
        payload.status,
        payload.reason,
        changed_by_id=current_user.id,
    )
    return ActionResponse(message="Booking status updated successfully")


@router.delete(
    "/{booking_id}",
    response_model=ActionResponse,
    summary="Delete a booking",
)
def delete_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    del current_user
    BookingService(db).delete_booking(booking_id)
    return ActionResponse(message="Booking deleted successfully")


@router.post(
    "/{booking_id}/travellers",
    response_model=SuccessResponse[BookingTravelerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a traveller to a booking",
)
def add_traveller(
    booking_id: uuid.UUID,
    payload: BookingTravelerCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> SuccessResponse[BookingTravelerResponse]:
    del current_user
    traveller = BookingService(db).add_traveller(booking_id, payload)
    return SuccessResponse(message="Traveller added successfully", data=traveller)


@router.patch(
    "/{booking_id}/travellers/{traveller_id}",
    response_model=ActionResponse,
    summary="Update booking traveller",
)
def update_traveller(
    booking_id: uuid.UUID,
    traveller_id: uuid.UUID,
    payload: BookingTravelerUpdate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    del current_user
    BookingService(db).update_traveller(booking_id, traveller_id, payload)
    return ActionResponse(message="Traveller updated successfully")


@router.delete(
    "/{booking_id}/travellers/{traveller_id}",
    response_model=ActionResponse,
    summary="Delete booking traveller",
)
def delete_traveller(
    booking_id: uuid.UUID,
    traveller_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_admin_or_staff),
) -> ActionResponse:
    del current_user
    BookingService(db).delete_traveller(booking_id, traveller_id)
    return ActionResponse(message="Traveller deleted successfully")
