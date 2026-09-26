import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import BookingStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.booking import (
    BookingResponse,
    BookingTravelerCreate,
    BookingTravelerResponse,
    BookingTravelerUpdate,
)
from app.schemas.customer_tour import CustomerTourDetailResponse
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse, SuccessResponse
from app.services.booking_service import BookingService

router = APIRouter(
    prefix="/customer-tours",
    tags=["Customer Tours"],
)


@router.get(
    "",
    response_model=PaginatedResponse[BookingResponse],
    responses={401: {"model": ErrorResponse}},
    summary="List my tours",
    description="Return paginated bookings belonging to the authenticated customer, newest first.",
)
def list_my_tours(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    month: int | None = Query(None, ge=1, le=12, description="Filter by travel month"),
    year: int | None = Query(None, ge=2000, le=2100, description="Filter by travel year"),
    status: str | None = Query(None, description="Filter by tour status"),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> PaginatedResponse[BookingResponse]:
    service = BookingService(db)
    # Parse status if valid BookingStatus
    booking_status = None
    if status:
        try:
            booking_status = BookingStatus(status.upper())
        except ValueError:
            pass

    bookings, total_items = service.list_my_bookings(
        customer_id=current_customer.id,
        page=page,
        page_size=page_size,
        month=month,
        year=year,
        status=booking_status,
    )
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return PaginatedResponse(
        message="Items fetched successfully",
        data=[BookingResponse.model_validate(booking) for booking in bookings],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get(
    "/{booking_id}",
    response_model=SuccessResponse[CustomerTourDetailResponse],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get my tour details",
    description="Return full details for a booking belonging to the authenticated customer.",
)
def get_my_tour_details(
    booking_id: uuid.UUID,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[CustomerTourDetailResponse]:
    booking = BookingService(db).get_booking_detail(
        booking_id,
        customer_id=current_customer.id,
    )
    return SuccessResponse(
        message="Booking details fetched successfully",
        data=CustomerTourDetailResponse.model_validate(booking.model_dump()),
    )


@router.post(
    "/{booking_id}/travellers",
    response_model=SuccessResponse[BookingTravelerResponse],
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Add a traveller to my booking",
)
def add_my_booking_traveller(
    booking_id: uuid.UUID,
    payload: BookingTravelerCreate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[BookingTravelerResponse]:
    traveller = BookingService(db).add_traveller(
        booking_id,
        payload,
        customer_id=current_customer.id,
    )
    return SuccessResponse(
        message="Traveller added successfully",
        data=BookingTravelerResponse.model_validate(traveller),
    )


@router.patch(
    "/{booking_id}/travellers/{traveller_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Update a traveller on my booking",
)
def update_my_booking_traveller(
    booking_id: uuid.UUID,
    traveller_id: uuid.UUID,
    payload: BookingTravelerUpdate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    BookingService(db).update_traveller(
        booking_id,
        traveller_id,
        payload,
        customer_id=current_customer.id,
    )
    return ActionResponse(message="Traveller updated successfully")


@router.delete(
    "/{booking_id}/travellers/{traveller_id}",
    response_model=ActionResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Remove a traveller from my booking",
)
def delete_my_booking_traveller(
    booking_id: uuid.UUID,
    traveller_id: uuid.UUID,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> ActionResponse:
    BookingService(db).delete_traveller(
        booking_id,
        traveller_id,
        customer_id=current_customer.id,
    )
    return ActionResponse(message="Traveller deleted successfully")

    


