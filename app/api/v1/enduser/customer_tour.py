from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import CustomerTourStatus
from app.db.database import get_db
from app.models.customer import Customer
from app.models.customer_tour import CustomerTour
from app.schemas.customer_tour import CustomerTourResponse
from app.schemas.response import ErrorResponse, SuccessResponse

router = APIRouter(
    prefix="/customer-tours",
    tags=["Customer Tours"],
)


def _list_customer_tours(
    db: Session,
    customer: Customer,
    month: int | None = None,
    year: int | None = None,
    status_filter: CustomerTourStatus | None = None,
) -> list[CustomerTourResponse]:
    query = db.query(CustomerTour).filter(CustomerTour.customer_id == customer.id)

    if month is not None:
        query = query.filter(CustomerTour.travel_date.is_not(None))
    if year is not None:
        query = query.filter(CustomerTour.travel_date.is_not(None))

    if month is not None or year is not None:
        if month is not None:
            query = query.filter(extract("month", CustomerTour.travel_date) == month)
        if year is not None:
            query = query.filter(extract("year", CustomerTour.travel_date) == year)

    if status_filter is not None:
        query = query.filter(CustomerTour.status == status_filter)

    tours = query.order_by(CustomerTour.travel_date.desc(), CustomerTour.created_at.desc()).all()
    return [CustomerTourResponse.model_validate(tour) for tour in tours]


@router.get(
    "",
    response_model=SuccessResponse[list[CustomerTourResponse]],
    responses={401: {"model": ErrorResponse}},
    summary="List my tours",
    description="Return all tours belonging to the authenticated customer, newest first.",
)
def list_my_tours(
    month: int | None = Query(None, ge=1, le=12, description="Filter by travel month"),
    year: int | None = Query(None, ge=2000, le=2100, description="Filter by travel year"),
    tour_status: CustomerTourStatus | None = Query(
        None,
        alias="status",
        description="Filter by tour status",
    ),
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[list[CustomerTourResponse]]:
    return SuccessResponse(
        message="Your tours fetched successfully",
        data=_list_customer_tours(
            db,
            current_customer,
            month=month,
            year=year,
            status_filter=tour_status,
        ),
    )