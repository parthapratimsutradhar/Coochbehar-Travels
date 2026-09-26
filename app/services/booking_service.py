from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import BookingSource, BookingStatus, LeadSource, PaymentStatus, TourType
from app.models.account import Account
from app.models.booking import Booking
from app.repository.booking_repo import BookingRepository
from app.repository.customer_repo import CustomerRepository
from app.services.financial_service import FinancialService
from app.services.email_service import EmailService
from app.services.booking_pdf_service import build_booking_pdf, generate_and_upload_booking_pdf
from app.schemas.booking import (
    BookingDetailResponse,
    BookingResponse,
    BookingTravelerCreate,
    BookingTravelerUpdate,
    OfflineBookingCreate,
    OnlineBookingCreate,
)


class BookingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.customer_repo = CustomerRepository(db)

    def _resolve_booking_travel_fields(
        self,
        payload: OfflineBookingCreate | OnlineBookingCreate,
    ) -> tuple[uuid.UUID | None, date | None, date | None]:
        package, variant, enquiry, departure = self.booking_repo.get_booking_reference_data(
            package_id=payload.package_id,
            variant_id=payload.variant_id,
            enquiry_id=payload.enquiry_id,
            departure_id=payload.departure_id,
        )

        destination_id = payload.destination_id
        if destination_id is None and package is not None:
            destination_id = package.destination_id
        if destination_id is None and enquiry is not None:
            destination_id = enquiry.destination_id

        departure_date = payload.departure_date
        if departure_date is None and departure is not None:
            departure_date = departure.departure_date
        if departure_date is None and enquiry is not None:
            departure_date = enquiry.travel_date

        return_date = payload.return_date
        if return_date is None and departure is not None:
            return_date = departure.return_date
        if return_date is None and departure_date is not None:
            if enquiry is not None and enquiry.travel_duration_day:
                return_date = departure_date + timedelta(days=enquiry.travel_duration_day - 1)
            elif enquiry is not None and enquiry.travel_duration_night is not None:
                return_date = departure_date + timedelta(days=enquiry.travel_duration_night)
            elif variant is not None and variant.duration_days > 0:
                return_date = departure_date + timedelta(days=variant.duration_days - 1)

        return destination_id, departure_date, return_date

    def create_offline_booking(self, payload: OfflineBookingCreate, staff_user: Account) -> Booking:
        destination_id, departure_date, return_date = self._resolve_booking_travel_fields(payload)
        primary_traveler = payload.travellers[0] if payload.travellers else None
        customer = None

        if payload.customer_id:
            customer = self.customer_repo.get_by_id(payload.customer_id)

        if not customer and primary_traveler is not None:
            if primary_traveler.mobile:
                customer = self.customer_repo.get_by_mobile(primary_traveler.mobile)
            if not customer and primary_traveler.email:
                customer = self.customer_repo.get_by_email(primary_traveler.email)

        if not customer and primary_traveler is not None:
            customer = self.customer_repo.create_customer(
                name=primary_traveler.full_name,
                mobile=primary_traveler.mobile,
                email=primary_traveler.email,
                source=LeadSource.OFFLINE,
            )

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A customer must be supplied either directly or via the first traveller record.",
            )

        booking_code = f"BK-OFF-{uuid.uuid4().hex[:6].upper()}"
        package_id = payload.package_id
        offer_id = payload.tour_offer_id
        total_amount = payload.total_selling_price
        advance = min(payload.advance_received, total_amount)
        due_amount = max(Decimal(0), total_amount - advance)

        status_val = (
            BookingStatus.FULLY_PAID
            if due_amount == Decimal(0) and advance > Decimal(0)
            else (BookingStatus.PARTIALLY_PAID if advance > Decimal(0) else BookingStatus.CONFIRMED)
        )

        booking_data = {
            "booking_code": booking_code,
            "customer_id": customer.id,
            "enquiry_id": payload.enquiry_id,
            "quotation_id": payload.quotation_id,
            "offer_id": offer_id,
            "package_id": package_id,
            "variant_id": payload.variant_id,
            "departure_id": payload.departure_id,
            "destination_id": destination_id,
            "departure_date": departure_date,
            "return_date": return_date,
            "booking_type": TourType.DOMESTIC,
            "source": payload.source or BookingSource.OFFLINE,
            "sales_account_id": payload.sales_account_id or staff_user.id,
            "status": status_val,
            "adult_count": payload.adult_count,
            "child_count": payload.child_count,
            "senior_count": payload.senior_count,
            "subtotal": total_amount,
            "discount_amount": Decimal(0),
            "total_amount": total_amount,
            "paid_amount": advance,
            "due_amount": due_amount,
            "notes": payload.special_notes,
            "created_by": staff_user.id,
        }

        travellers_data = [traveller.model_dump(exclude_none=True) for traveller in payload.travellers]

        cost_items = payload.costs if payload.costs is not None else payload.items
        itinerary_data = [day.model_dump(exclude_none=True) for day in payload.itinerary]
        if departure_date or return_date:
            itinerary_dates = {
                day["date"].date() if isinstance(day.get("date"), datetime) else day.get("date")
                for day in itinerary_data
                if day.get("date") is not None
            }
            date_labels = (
                (departure_date, "Departure Day"),
                (return_date, "Return Day"),
            )
            next_day_number = max((day["day_number"] for day in itinerary_data), default=0) + 1
            next_sort_order = max((day["sort_order"] for day in itinerary_data), default=-1) + 1
            for travel_day, title in date_labels:
                if travel_day is not None and travel_day not in itinerary_dates:
                    itinerary_data.append(
                        {
                            "day_number": next_day_number,
                            "date": datetime.combine(travel_day, time.min, tzinfo=timezone.utc),
                            "title": title,
                            "sort_order": next_sort_order,
                        }
                    )
                    itinerary_dates.add(travel_day)
                    next_day_number += 1
                    next_sort_order += 1

        booking = self.booking_repo.create(
            booking_data,
            travellers=travellers_data,
            items=[item.model_dump(exclude_none=True) for item in cost_items],
            hotels=[hotel.model_dump(exclude_none=True) for hotel in payload.hotels],
            vehicles=[vehicle.model_dump(exclude_none=True) for vehicle in payload.vehicles],
            itinerary=itinerary_data,
        )

        # 2. Record advance payment if present
        if advance > Decimal(0):
            self.db.commit()
            FinancialService(self.db).record_booking_payment(
                booking_id=booking.id,
                customer_id=booking.customer_id,
                amount=advance,
                currency="INR",
                payment_method=payload.payment_mode,
                payment_status=PaymentStatus.SUCCESS,
                gateway=None,
                gateway_transaction_id=None,
                external_reference=f"offline-booking-advance:{booking.id}",
                description=f"Initial advance payment for offline booking {booking_code}",
                recorded_by_account_id=staff_user.id,
                transaction_date=None,
            )

        return booking

    def create_online_booking(self, payload: OnlineBookingCreate, customer: Account) -> Booking:
        destination_id, departure_date, return_date = self._resolve_booking_travel_fields(payload)
        booking_code = f"BK-{uuid.uuid4().hex[:8].upper()}"
        booking_data = {
            "booking_code": booking_code,
            "customer_id": customer.id,
            "enquiry_id": payload.enquiry_id,
            "quotation_id": payload.quotation_id,
            "package_id": payload.package_id,
            "variant_id": payload.variant_id,
            "departure_id": payload.departure_id,
            "destination_id": destination_id,
            "departure_date": departure_date,
            "return_date": return_date,
            "booking_type": TourType.DOMESTIC,
            "source": payload.source or BookingSource.WEBSITE,
            "status": BookingStatus.TENTATIVE,
            "adult_count": payload.adult_count,
            "child_count": payload.child_count,
            "senior_count": payload.senior_count,
            "subtotal": Decimal(0),
            "discount_amount": Decimal(0),
            "total_amount": Decimal(0),
            "paid_amount": Decimal(0),
            "due_amount": Decimal(0),
            "notes": payload.notes,
            "created_by": customer.id,
        }
        travellers_data = [t.model_dump() for t in payload.travellers]
        return self.booking_repo.create(booking_data, travellers=travellers_data)

    def get_booking(self, booking_id: uuid.UUID) -> Booking:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        return booking

    def get_booking_detail(self, booking_id: uuid.UUID) -> BookingDetailResponse:
        booking = self.get_booking(booking_id)
        costs = list(booking.trip_items)
        total_costs = sum((c.total_price for c in costs), Decimal(0))
        gross_profit = booking.total_amount - total_costs
        margin = (
            round(float((gross_profit / booking.total_amount) * 100), 2)
            if booking.total_amount > Decimal(0)
            else 0.0
        )

        detail = BookingDetailResponse.model_validate(booking)
        detail.customer_name = booking.customer.name if booking.customer else None
        detail.customer_mobile = booking.customer.mobile if booking.customer else None
        detail.gross_profit = gross_profit
        detail.profit_margin = margin
        return detail

    def list_all_bookings(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: uuid.UUID | None = None,
        month: int | None = None,
        year: int | None = None,
        status: BookingStatus | None = None,
        source: BookingSource | None = None,
        search: str | None = None,
    ) -> dict:
        items, total = self.booking_repo.list_all(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            month=month,
            year=year,
            status=status,
            source=source,
            search=search,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def list_my_bookings(
        self,
        customer_id: uuid.UUID,
        month: int | None = None,
        year: int | None = None,
        status: BookingStatus | None = None,
    ) -> list[Booking]:
        return self.booking_repo.list_for_customer(
            customer_id=customer_id,
            month=month,
            year=year,
            status=status,
        )

    def update_booking_status(
        self,
        booking_id: uuid.UUID,
        new_status: BookingStatus,
        reason: str | None = None,
        changed_by_id: uuid.UUID | None = None,
    ) -> Booking:
        booking = self.get_booking(booking_id)
        return self.booking_repo.update_status(
            booking,
            new_status,
            reason=reason,
            changed_by_id=changed_by_id,
        )

    def delete_booking(self, booking_id: uuid.UUID) -> None:
        self.booking_repo.delete(self.get_booking(booking_id))

    def list_bookings_for_day(self, travel_day: date) -> list[Booking]:
        return self.booking_repo.list_for_day(travel_day)

    async def generate_booking_pdf(self, booking_id: uuid.UUID) -> dict:
        return await generate_and_upload_booking_pdf(self.get_booking(booking_id))

    def render_booking_pdf(self, booking_id: uuid.UUID) -> tuple[str, bytes]:
        booking = self.get_booking(booking_id)
        return booking.booking_code, build_booking_pdf(booking)

    async def email_booking(self, booking_id: uuid.UUID, recipient_email: str) -> str:
        booking = self.get_booking(booking_id)
        uploaded = await generate_and_upload_booking_pdf(booking)
        pdf_url = uploaded.get("secure_url") or uploaded.get("url")
        if not pdf_url:
            raise HTTPException(status_code=502, detail="Booking PDF upload did not return a download URL.")
        customer_name = booking.customer.name if booking.customer else "Customer"
        EmailService().send_email(
            recipient_email,
            f"Booking {booking.booking_code} - {booking.package.title if booking.package else 'Travel booking'}",
            f"Dear {customer_name},\n\nYour booking PDF is available here:\n{pdf_url}\n\nRegards,\nCoochbehar Travels",
        )
        return pdf_url

    def add_traveller(self, booking_id: uuid.UUID, payload: BookingTravelerCreate) -> dict:
        booking = self.get_booking(booking_id)
        from app.models.booking_traveler import BookingTraveler
        traveler = BookingTraveler(booking_id=booking.id, **payload.model_dump())
        self.db.add(traveler)
        self.db.commit()
        self.db.refresh(traveler)
        return traveler

    def update_traveller(self, booking_id: uuid.UUID, traveller_id: uuid.UUID, payload: BookingTravelerUpdate):
        booking = self.get_booking(booking_id)
        traveller = next((item for item in booking.travellers if item.id == traveller_id), None)
        if traveller is None:
            raise HTTPException(status_code=404, detail="Traveller not found.")
        return self.booking_repo.update_traveller(traveller, payload.model_dump(exclude_unset=True))

    def delete_traveller(self, booking_id: uuid.UUID, traveller_id: uuid.UUID) -> None:
        booking = self.get_booking(booking_id)
        traveller = next((item for item in booking.travellers if item.id == traveller_id), None)
        if traveller is None:
            raise HTTPException(status_code=404, detail="Traveller not found.")
        self.booking_repo.delete_traveller(traveller)
