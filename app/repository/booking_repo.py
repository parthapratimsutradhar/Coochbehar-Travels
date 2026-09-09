from decimal import Decimal
import uuid
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import BookingSource, BookingStatus
from app.models.booking import Booking
from app.models.booking_costs import BookingCost
from app.models.booking_status_history import BookingStatusHistory
from app.models.booking_traveler import BookingTraveler


class BookingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.travellers),
                joinedload(Booking.package),
                joinedload(Booking.variant),
                joinedload(Booking.departure),
                joinedload(Booking.customer),
                joinedload(Booking.status_history),
                joinedload(Booking.payments),
            )
            .where(Booking.id == booking_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_code(self, booking_code: str) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.travellers),
                joinedload(Booking.package),
                joinedload(Booking.customer),
            )
            .where(Booking.booking_code == booking_code)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: BookingStatus | None = None,
        source: BookingSource | None = None,
        search: str | None = None,
    ) -> tuple[list[Booking], int]:
        stmt = select(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.package),
        )
        if status is not None:
            stmt = stmt.where(Booking.status == status)
        if source is not None:
            stmt = stmt.where(Booking.source == source)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(Booking.booking_code.ilike(term))

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        bookings = self.db.execute(
            stmt.order_by(Booking.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).unique().scalars().all()
        return list(bookings), total

    def list_for_customer(
        self,
        customer_id: uuid.UUID,
        month: int | None = None,
        year: int | None = None,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .options(joinedload(Booking.package), joinedload(Booking.variant), joinedload(Booking.departure))
            .where(Booking.customer_id == customer_id)
        )
        if status is not None:
            stmt = stmt.where(Booking.status == status)
        if month is not None:
            stmt = stmt.where(extract("month", Booking.created_at) == month)
        if year is not None:
            stmt = stmt.where(extract("year", Booking.created_at) == year)

        stmt = stmt.order_by(Booking.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())

    def create(
        self,
        booking_data: dict,
        travellers: list[dict] | None = None,
        costs: list[dict] | None = None,
    ) -> Booking:
        booking = Booking(**booking_data)
        self.db.add(booking)
        self.db.flush()

        if travellers:
            for tr in travellers:
                traveler = BookingTraveler(booking_id=booking.id, **tr)
                self.db.add(traveler)

        if costs:
            for c in costs:
                cost = BookingCost(booking_id=booking.id, **c)
                self.db.add(cost)

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=None,
            status=booking.status,
            notes="Initial booking creation",
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(booking)
        return booking

    def update(self, booking: Booking, update_data: dict) -> Booking:
        for k, v in update_data.items():
            if v is not None:
                setattr(booking, k, v)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def update_status(
        self,
        booking: Booking,
        new_status: BookingStatus,
        reason: str | None = None,
    ) -> Booking:
        old_status = booking.status
        booking.status = new_status

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_status,
            status=new_status,
            notes=reason,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def add_cost(self, booking_id: uuid.UUID, cost_data: dict) -> BookingCost:
        cost = BookingCost(booking_id=booking_id, **cost_data)
        self.db.add(cost)
        self.db.commit()
        self.db.refresh(cost)
        return cost

    def get_costs_for_booking(self, booking_id: uuid.UUID) -> list[BookingCost]:
        stmt = select(BookingCost).where(BookingCost.booking_id == booking_id)
        return list(self.db.execute(stmt).scalars().all())

    def update_financials(self, booking: Booking, payment_amount: Decimal) -> Booking:
        booking.paid_amount += payment_amount
        booking.due_amount = max(Decimal(0), booking.total_amount - booking.paid_amount)
        if booking.due_amount == Decimal(0):
            booking.status = BookingStatus.FULLY_PAID
        elif booking.paid_amount > Decimal(0):
            booking.status = BookingStatus.PARTIALLY_PAID
        self.db.commit()
        self.db.refresh(booking)
        return booking
