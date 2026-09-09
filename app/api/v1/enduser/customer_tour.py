from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import BookingStatus
from app.db.database import get_db
from app.models.account import Account
from app.schemas.customer_tour import CustomerTourResponse
from app.schemas.response import ErrorResponse, SuccessResponse
from app.services.booking_service import BookingService

router = APIRouter(
    prefix="/customer-tours",
    tags=["Customer Tours"],
)


@router.get(
    "",
    response_model=SuccessResponse[list[CustomerTourResponse]],
    responses={401: {"model": ErrorResponse}},
    summary="List my tours",
    description="Return all booked tours belonging to the authenticated customer, newest first.",
)
def list_my_tours(
    month: int | None = Query(None, ge=1, le=12, description="Filter by travel month"),
    year: int | None = Query(None, ge=2000, le=2100, description="Filter by travel year"),
    status: str | None = Query(None, description="Filter by tour status"),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[list[CustomerTourResponse]]:
    service = BookingService(db)
    # Parse status if valid BookingStatus
    booking_status = None
    if status:
        try:
            booking_status = BookingStatus(status.upper())
        except ValueError:
            pass

    bookings = service.list_my_bookings(
        customer_id=current_customer.id,
        month=month,
        year=year,
        status=booking_status,
    )

    items = []
    for b in bookings:
        pax = b.adult_count + b.child_count + b.senior_count
        tour_name = b.package.title if b.package else f"Tour {b.booking_code}"
        destination = b.package.destination if b.package else None
        travel_date = b.departure.departure_date if b.departure else None
        items.append(
            CustomerTourResponse(
                id=b.id,
                tour_name=tour_name,
                destination=destination,
                travel_date=travel_date,
                return_date=None,
                pax_no=pax,
                total_amount=b.total_amount,
                status=b.status.value,
                notes=b.notes,
                package_id=b.package_id,
                variant_id=b.variant_id,
                enquiry_id=b.enquiry_id,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )

    return SuccessResponse(
        message="Your tours fetched successfully",
        data=items,
    )