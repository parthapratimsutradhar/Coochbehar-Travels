from decimal import Decimal
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.enums import BookingSource, BookingStatus
from app.models.booking import Booking
from app.models.booking_status_history import BookingStatusHistory
from app.models.booking_traveler import BookingTraveler
from app.models.enquiry import Enquiry
from app.models.trip_items import TripItem
from app.models.trip_itinerary import TripItinerary
from app.models.trip_hotel import TripHotel
from app.models.trip_vehicle import TripVehicle
from app.models.tour_variant import TourVariant


class BookingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.travellers),
                joinedload(Booking.customer),
                joinedload(Booking.enquiry).joinedload(Enquiry.destination_ref),
                joinedload(Booking.package),
                joinedload(Booking.variant).joinedload(TourVariant.details),
                joinedload(Booking.departure),
                joinedload(Booking.offer),
                joinedload(Booking.sales_account),
                joinedload(Booking.created_by_account),
                joinedload(Booking.status_history),
                joinedload(Booking.trip_items).joinedload(TripItem.hotel),
                joinedload(Booking.trip_items).joinedload(TripItem.vehicle),
                joinedload(Booking.trip_itinerary),
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
                joinedload(Booking.trip_items).joinedload(TripItem.hotel),
                joinedload(Booking.trip_items).joinedload(TripItem.vehicle),
                joinedload(Booking.trip_itinerary),
            )
            .where(Booking.booking_code == booking_code)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: uuid.UUID | None = None,
        month: int | None = None,
        year: int | None = None,
        status: BookingStatus | None = None,
        source: BookingSource | None = None,
        search: str | None = None,
    ) -> tuple[list[Booking], int]:
        stmt = select(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.enquiry).joinedload(Enquiry.destination_ref),
            joinedload(Booking.package),
            joinedload(Booking.variant).joinedload(TourVariant.details),
            joinedload(Booking.departure),
            joinedload(Booking.offer),
            joinedload(Booking.sales_account),
            joinedload(Booking.created_by_account),
            joinedload(Booking.trip_items).joinedload(TripItem.hotel),
            joinedload(Booking.trip_items).joinedload(TripItem.vehicle),
            joinedload(Booking.trip_itinerary),
        )
        if status is not None:
            stmt = stmt.where(Booking.status == status)
        if customer_id is not None:
            stmt = stmt.where(Booking.customer_id == customer_id)
        if month is not None:
            stmt = stmt.where(func.extract("month", Booking.created_at) == month)
        if year is not None:
            stmt = stmt.where(func.extract("year", Booking.created_at) == year)
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

    def list_for_day(self, travel_day) -> list[Booking]:
        stmt = (
            select(Booking)
            .outerjoin(Enquiry, Enquiry.id == Booking.enquiry_id)
            .outerjoin(TripItinerary, TripItinerary.booking_id == Booking.id)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.package),
                joinedload(Booking.variant),
                joinedload(Booking.travellers),
                joinedload(Booking.trip_items).joinedload(TripItem.hotel),
                joinedload(Booking.trip_items).joinedload(TripItem.vehicle),
                joinedload(Booking.trip_itinerary),
            )
            .where(
                (Enquiry.travel_date == travel_day)
                | (func.date(TripItinerary.date) == travel_day)
            )
            .order_by(Booking.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_offer(self, offer_id: uuid.UUID) -> list[Booking]:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.package),
                joinedload(Booking.variant),
                joinedload(Booking.departure),
                joinedload(Booking.travellers),
                joinedload(Booking.status_history),
            )
            .where(Booking.offer_id == offer_id)
            .order_by(Booking.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def create(
        self,
        booking_data: dict,
        travellers: list[dict] | None = None,
        items: list[dict] | None = None,
        hotels: list[dict] | None = None,
        vehicles: list[dict] | None = None,
        itinerary: list[dict] | None = None,
    ) -> Booking:
        booking = Booking(**booking_data)
        self.db.add(booking)
        self.db.flush()

        if travellers:
            for tr in travellers:
                traveler = BookingTraveler(booking_id=booking.id, **tr)
                self.db.add(traveler)

        created_items = []
        for index, item_data in enumerate(items or []):
            item = TripItem(booking_id=booking.id, **item_data)
            item.sort_order = index
            self.db.add(item)
            self.db.flush()
            created_items.append(item)
        for item, hotel_data in zip(
            [item for item in created_items if item.item_type.value == "hotel"],
            hotels or [],
        ):
            self.db.add(TripHotel(trip_item_id=item.id, **hotel_data))
        for item, vehicle_data in zip(
            [item for item in created_items if item.item_type.value in {"transport", "transfer"}],
            vehicles or [],
        ):
            self.db.add(TripVehicle(trip_item_id=item.id, **vehicle_data))
        for day in itinerary or []:
            self.db.add(TripItinerary(booking_id=booking.id, **day))

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=None,
            new_status=booking.status,
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
        changed_by_id: uuid.UUID | None = None,
    ) -> Booking:
        old_status = booking.status
        booking.status = new_status

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            notes=reason,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def delete(self, booking: Booking) -> None:
        self.db.delete(booking)
        self.db.commit()

    def update_traveller(self, traveller: BookingTraveler, data: dict) -> BookingTraveler:
        for key, value in data.items():
            if value is not None:
                setattr(traveller, key, value)
        self.db.commit()
        self.db.refresh(traveller)
        return traveller

    def delete_traveller(self, traveller: BookingTraveler) -> None:
        self.db.delete(traveller)
        self.db.commit()

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
