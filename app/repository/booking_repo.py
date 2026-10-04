from decimal import Decimal
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.account import Account
from app.core.enums import BookingSource, BookingStatus
from app.models.booking import Booking
from app.models.booking_status_history import BookingStatusHistory
from app.models.booking_traveler import BookingTraveler
from app.models.enquiry import Enquiry
from app.models.trip_items import TripItem
from app.models.trip_itinerary import TripItinerary
from app.models.trip_hotel import TripHotel
from app.models.trip_vehicle import TripVehicle
from app.models.tour_departure import TourDeparture
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.utils.booking_traveller import ensure_unique_booking_travellers


class BookingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _contact_matches(value: str | None, expected: str | None) -> bool:
        return bool(
            value
            and expected
            and value.strip().casefold() == expected.strip().casefold()
        )

    def _apply_primary_traveller_flags(self, customer_id, travellers) -> None:
        customer = self.db.get(Account, customer_id)
        primary_index = None

        if customer is not None and customer.mobile:
            primary_index = next(
                (
                    index
                    for index, traveller in enumerate(travellers)
                    if self._contact_matches(
                        traveller.get("mobile")
                        if isinstance(traveller, dict)
                        else traveller.mobile,
                        customer.mobile,
                    )
                ),
                None,
            )

        if primary_index is None and customer is not None and customer.email:
            primary_index = next(
                (
                    index
                    for index, traveller in enumerate(travellers)
                    if self._contact_matches(
                        traveller.get("email")
                        if isinstance(traveller, dict)
                        else traveller.email,
                        customer.email,
                    )
                ),
                None,
            )

        for index, traveller in enumerate(travellers):
            if isinstance(traveller, dict):
                traveller["is_primary"] = index == primary_index
            else:
                traveller.is_primary = index == primary_index

    def sync_primary_travellers(self, booking: Booking) -> None:
        self._apply_primary_traveller_flags(booking.customer_id, booking.travellers)

    def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.travellers),
                joinedload(Booking.customer),
                joinedload(Booking.enquiry).joinedload(Enquiry.destination_ref),
                joinedload(Booking.destination),
                joinedload(Booking.package).joinedload(TourPackage.destination),
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

    def get_for_update(self, booking_id: uuid.UUID) -> Booking | None:
        return self.db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()

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

    def get_by_idempotency_key(self, customer_id: uuid.UUID, idempotency_key: str) -> Booking | None:
        return self.db.execute(
            select(Booking).where(
                Booking.customer_id == customer_id,
                Booking.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()

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
            joinedload(Booking.destination),
            joinedload(Booking.package).joinedload(TourPackage.destination),
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

    def get_booking_reference_data(
        self,
        package_id: uuid.UUID | None,
        variant_id: uuid.UUID | None,
        enquiry_id: uuid.UUID | None,
        departure_id: uuid.UUID | None,
    ) -> tuple[TourPackage | None, TourVariant | None, Enquiry | None, TourDeparture | None]:
        package = self.db.get(TourPackage, package_id) if package_id else None
        variant = self.db.get(TourVariant, variant_id) if variant_id else None
        enquiry = self.db.get(Enquiry, enquiry_id) if enquiry_id else None
        departure = self.db.get(TourDeparture, departure_id) if departure_id else None
        if package is None and enquiry is not None and enquiry.package_id:
            package = self.db.get(TourPackage, enquiry.package_id)
        if variant is None and enquiry is not None and enquiry.variant_id:
            variant = self.db.get(TourVariant, enquiry.variant_id)
        if variant is None and departure is not None:
            variant = departure.variant
        if package is None and variant is not None:
            package = variant.package
        return package, variant, enquiry, departure

    def list_for_customer(
        self,
        customer_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        month: int | None = None,
        year: int | None = None,
        status: BookingStatus | None = None,
    ) -> tuple[list[Booking], int]:
        itinerary_start = (
            select(func.min(TripItinerary.date))
            .where(TripItinerary.booking_id == Booking.id)
            .scalar_subquery()
        )
        travel_date = func.coalesce(
            Booking.departure_date,
            TourDeparture.departure_date,
            func.date(itinerary_start),
            Enquiry.travel_date,
        )
        stmt = (
            select(Booking)
            .outerjoin(TourDeparture, Booking.departure_id == TourDeparture.id)
            .outerjoin(Enquiry, Booking.enquiry_id == Enquiry.id)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.destination),
                joinedload(Booking.package).joinedload(TourPackage.destination),
                joinedload(Booking.variant).joinedload(TourVariant.details),
                joinedload(Booking.departure),
                joinedload(Booking.enquiry).joinedload(Enquiry.destination_ref),
                joinedload(Booking.trip_itinerary),
            )
            .where(Booking.customer_id == customer_id)
        )
        if status is not None:
            stmt = stmt.where(Booking.status == status)
        if month is not None:
            stmt = stmt.where(func.extract("month", travel_date) == month)
        if year is not None:
            stmt = stmt.where(func.extract("year", travel_date) == year)

        total = self.db.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()
        bookings = self.db.execute(
            stmt.order_by(Booking.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().scalars().all()
        return list(bookings), total

    def list_for_day(self, travel_day) -> list[Booking]:
        stmt = (
            select(Booking)
            .outerjoin(Enquiry, Enquiry.id == Booking.enquiry_id)
            .outerjoin(TripItinerary, TripItinerary.booking_id == Booking.id)
            .options(
                joinedload(Booking.customer),
                joinedload(Booking.enquiry).joinedload(Enquiry.destination_ref),
                joinedload(Booking.destination),
                joinedload(Booking.package).joinedload(TourPackage.destination),
                joinedload(Booking.variant).joinedload(TourVariant.details),
                joinedload(Booking.departure),
                joinedload(Booking.offer),
                joinedload(Booking.sales_account),
                joinedload(Booking.created_by_account),
                selectinload(Booking.travellers),
                selectinload(Booking.trip_items).joinedload(TripItem.hotel),
                selectinload(Booking.trip_items).joinedload(TripItem.vehicle),
                selectinload(Booking.trip_itinerary),
                selectinload(Booking.status_history),
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
        commit: bool = True,
    ) -> Booking:
        booking = Booking(**booking_data)
        seat_count = self._booking_seat_count(booking, travellers)
        if booking.departure_id is not None and seat_count > 0:
            self._reserve_departure_seats(
                booking.departure_id,
                seat_count,
                expected_variant_id=booking.variant_id,
            )
            booking.departure_seats_reserved = seat_count
        travellers = [dict(traveller) for traveller in travellers or []]
        ensure_unique_booking_travellers(travellers)
        self._apply_primary_traveller_flags(booking.customer_id, travellers)
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

        if commit:
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
        commit: bool = True,
    ) -> Booking:
        old_status = booking.status
        old_is_cancelled = old_status in {BookingStatus.CANCELLED, BookingStatus.REFUNDED}
        new_is_cancelled = new_status in {BookingStatus.CANCELLED, BookingStatus.REFUNDED}
        if booking.departure_id is not None and not old_is_cancelled and new_is_cancelled:
            if booking.departure_seats_reserved > 0:
                self._restore_departure_seats(booking.departure_id, booking.departure_seats_reserved)
                booking.departure_seats_reserved = 0
        elif booking.departure_id is not None and old_is_cancelled and not new_is_cancelled:
            seat_count = self._booking_seat_count(booking, booking.travellers)
            if seat_count > 0:
                self._reserve_departure_seats(
                    booking.departure_id,
                    seat_count,
                    expected_variant_id=booking.variant_id,
                )
                booking.departure_seats_reserved = seat_count
        booking.status = new_status

        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=old_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            notes=reason,
        )
        self.db.add(history)
        if commit:
            self.db.commit()
            self.db.refresh(booking)
        return booking

    def delete(self, booking: Booking) -> None:
        if booking.departure_id is not None and booking.departure_seats_reserved > 0:
            self._restore_departure_seats(booking.departure_id, booking.departure_seats_reserved)
        self.db.delete(booking)
        self.db.commit()

    def adjust_departure_seats(self, booking: Booking, count_delta: int) -> None:
        if booking.departure_id is None or booking.status in {
            BookingStatus.CANCELLED,
            BookingStatus.REFUNDED,
        }:
            return
        if count_delta > 0:
            self._reserve_departure_seats(
                booking.departure_id,
                count_delta,
                expected_variant_id=booking.variant_id,
            )
            booking.departure_seats_reserved += count_delta
        elif count_delta < 0:
            seats_to_restore = min(-count_delta, booking.departure_seats_reserved)
            if seats_to_restore:
                self._restore_departure_seats(booking.departure_id, seats_to_restore)
                booking.departure_seats_reserved -= seats_to_restore

    def _reserve_departure_seats(
        self,
        departure_id: uuid.UUID,
        count: int,
        *,
        expected_variant_id: uuid.UUID | None,
    ) -> None:
        departure = self.db.execute(
            select(TourDeparture)
            .where(TourDeparture.id == departure_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if departure is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour departure not found.")
        if not departure.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tour departure is not active.")
        if expected_variant_id is not None and departure.variant_id != expected_variant_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Departure does not match the selected tour variant.")
        if departure.available_seats < count:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Not enough seats available for this departure.")
        departure.available_seats -= count

    def _restore_departure_seats(self, departure_id: uuid.UUID, count: int) -> None:
        departure = self.db.execute(
            select(TourDeparture)
            .where(TourDeparture.id == departure_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if departure is not None:
            departure.available_seats = min(departure.total_seats, departure.available_seats + count)

    @staticmethod
    def _booking_seat_count(booking: Booking, travellers: list | None) -> int:
        if travellers:
            return len(travellers)
        return booking.adult_count + booking.child_count + booking.senior_count

    def update_traveller(self, traveller: BookingTraveler, data: dict) -> BookingTraveler:
        identity_fields = ("full_name", "mobile", "email")
        updated_identity = {
            field: getattr(traveller, field)
            for field in identity_fields
        }
        updated_identity.update(
            {
                field: value
                for field, value in data.items()
                if field in identity_fields and value is not None
            }
        )
        ensure_unique_booking_travellers(
            [updated_identity],
            existing=(
                saved
                for saved in traveller.booking.travellers
                if saved.id != traveller.id
            ),
        )
        for key, value in data.items():
            if value is not None:
                setattr(traveller, key, value)
        self.sync_primary_travellers(traveller.booking)
        self.db.commit()
        self.db.refresh(traveller)
        return traveller

    def delete_traveller(self, traveller: BookingTraveler, *, commit: bool = True) -> None:
        self.db.delete(traveller)
        if commit:
            self.db.commit()

    def update_financials(
        self,
        booking: Booking,
        payment_amount: Decimal,
        *,
        commit: bool = True,
    ) -> Booking:
        booking.paid_amount += payment_amount
        booking.due_amount = max(Decimal(0), booking.total_amount - booking.paid_amount)
        if booking.due_amount == Decimal(0):
            booking.status = BookingStatus.FULLY_PAID
        elif booking.paid_amount > Decimal(0):
            booking.status = BookingStatus.PARTIALLY_PAID
        if commit:
            self.db.commit()
            self.db.refresh(booking)
        return booking
