from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import TYPE_CHECKING
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import BookingSource, BookingStatus, EnquiryStatus, QuotationStatus
from app.models.account import Account
from app.models.quotation import Quotation
from app.repository.enquiry_repo import EnquiryRepository
from app.repository.quotation_repo import QuotationRepository
from app.schemas.quotation import QuotationCreate, QuotationUpdate, QuotationVersionCreate
from app.services.email_service import EmailService
from app.services.quotation_pdf_service import generate_and_upload_quotation_pdf

if TYPE_CHECKING:
    from app.models.booking import Booking


class QuotationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quotation_repo = QuotationRepository(db)
        self.enquiry_repo = EnquiryRepository(db)

    def create_quotation(self, payload: QuotationCreate, staff_user: Account) -> Quotation:
        enquiry = self.enquiry_repo.get_by_id(payload.enquiry_id)
        if not enquiry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found.")

        # Version calculation
        enquiry_id = payload.enquiry_id
        version = self.quotation_repo.get_latest_version(enquiry_id) + 1
        quotation_code = f"QT-{enquiry.enquiry_code}-V{version}"

        # Calculate totals from items if provided
        items_data = [item.model_dump() for item in payload.items]
        for item in items_data:
            item["total_price"] = item["unit_price"] * item["quantity"]
        subtotal = payload.subtotal
        if items_data and subtotal == Decimal(0):
            subtotal = sum((it["unit_price"] * it["quantity"] for it in items_data), Decimal(0))
        total_amount = max(Decimal(0), subtotal - payload.discount_amount + payload.tax_amount)

        quotation_data = {
            "quotation_code": quotation_code,
            "version": version,
            "customer_id": enquiry.customer_id,
            "enquiry_id": payload.enquiry_id,
            "package_id": payload.package_id,
            "variant_id": payload.variant_id,
            "destination_id": payload.destination_id,
            "tour_name": payload.tour_name,
            "travel_date": payload.travel_date,
            "return_date": payload.return_date,
            "subtotal": subtotal,
            "discount_amount": payload.discount_amount,
            "tax_amount": payload.tax_amount,
            "total_amount": total_amount,
            "valid_until": payload.valid_until,
            "status": QuotationStatus.DRAFT,
            "terms_and_conditions": payload.terms_and_conditions,
            "important_notes": payload.important_notes,
            "inclusion": payload.inclusion,
            "exclusion": payload.exclusion,
            "created_by_account_id": staff_user.id,
        }

        quotation = self.quotation_repo.create(
            quotation_data,
            items=items_data,
            hotels=[hotel.model_dump() for hotel in payload.hotels],
            vehicles=[vehicle.model_dump() for vehicle in payload.vehicles],
            itinerary=[item.model_dump() for item in payload.itinerary],
        )

        if enquiry:
            self.enquiry_repo.update_status(enquiry, EnquiryStatus.QUOTED)

        return quotation

    def get_quotation(self, quotation_id: uuid.UUID) -> Quotation:
        q = self.quotation_repo.get_by_id(quotation_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        return q

    def list_all_quotations(
        self,
        page: int = 1,
        page_size: int = 20,
        status: QuotationStatus | None = None,
        search: str | None = None,
    ) -> dict:
        items, total = self.quotation_repo.list_all(page=page, page_size=page_size, status=status, search=search)
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def list_enquiry_quotations(self, enquiry_id: uuid.UUID) -> list[Quotation]:
        return self.quotation_repo.list_for_enquiry(enquiry_id)

    def list_customer_quotations(self, customer_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[Quotation]:
        return self.quotation_repo.list_for_customer(customer_id, skip=skip, limit=limit)

    def create_quotation_version(
        self,
        quotation_id: uuid.UUID,
        payload: QuotationVersionCreate,
        staff_user: Account,
    ) -> Quotation:
        previous = self.get_quotation(quotation_id)
        if previous.status != QuotationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a rejected quotation can be revised into a new version.",
            )
        if not previous.enquiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation is not linked to an enquiry.",
            )

        values = payload.model_dump(exclude_unset=True)
        items_data = values.pop("items", None)
        hotels_data = values.pop("hotels", None)
        vehicles_data = values.pop("vehicles", None)
        itinerary_data = values.pop("itinerary", None)

        if items_data is None:
            items_data = [
                {
                    "item_type": item.item_type,
                    "name": item.name,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                }
                for item in previous.items
            ]
        else:
            for item in items_data:
                item["total_price"] = item["unit_price"] * item["quantity"]

        if hotels_data is None:
            hotels_data = [
                {
                    "hotel_id": item.hotel.hotel_id,
                    "hotel_name": item.hotel.hotel_name,
                    "check_in": item.hotel.check_in,
                    "check_out": item.hotel.check_out,
                    "nights": item.hotel.nights,
                    "room_count": item.hotel.room_count,
                    "room_type": item.hotel.room_type,
                }
                for item in previous.items
                if item.hotel
            ]
        if vehicles_data is None:
            vehicles_data = [
                {
                    "vehicle_id": item.vehicle.vehicle_id,
                    "vehicle_name": item.vehicle.vehicle_name,
                    "vehicle_type": item.vehicle.vehicle_type,
                    "start_date": item.vehicle.start_date,
                    "end_date": item.vehicle.end_date,
                    "rental_minutes": item.vehicle.rental_minutes,
                    "quantity": item.vehicle.quantity,
                }
                for item in previous.items
                if item.vehicle
            ]

        if itinerary_data is None:
            itinerary_data = [
                {
                    "day_number": day.day_number,
                    "date": day.date,
                    "title": day.title,
                    "description": day.description,
                    "overnight_location": day.overnight_location,
                    "meal_plan": day.meal_plan,
                    "sort_order": day.sort_order,
                }
                for day in previous.itinerary
            ]

        if "subtotal" not in values and items_data:
            values["subtotal"] = sum(
                (item["unit_price"] * item["quantity"] for item in items_data),
                Decimal(0),
            )
        subtotal = values.get("subtotal", previous.subtotal)
        discount = values.get("discount_amount", previous.discount_amount)
        tax = values.get("tax_amount", previous.tax_amount)
        values["total_amount"] = max(Decimal(0), subtotal - discount + tax)

        version = self.quotation_repo.get_latest_version(previous.enquiry_id) + 1
        quotation_data = {
            "quotation_code": f"QT-{previous.enquiry.enquiry_code}-V{version}",
            "version": version,
            "customer_id": previous.customer_id,
            "enquiry_id": previous.enquiry_id,
            "package_id": values.pop("package_id", previous.package_id),
            "variant_id": values.pop("variant_id", previous.variant_id),
            "destination_id": values.pop("destination_id", previous.destination_id),
            "tour_name": values.pop("tour_name", previous.tour_name),
            "travel_date": values.pop("travel_date", previous.travel_date),
            "return_date": values.pop("return_date", previous.return_date),
            "subtotal": subtotal,
            "discount_amount": discount,
            "tax_amount": tax,
            "total_amount": values.pop("total_amount"),
            "valid_until": values.pop("valid_until", previous.valid_until),
            "status": QuotationStatus.DRAFT,
            "terms_and_conditions": values.pop("terms_and_conditions", previous.terms_and_conditions),
            "important_notes": values.pop("important_notes", previous.important_notes),
            "inclusion": values.pop("inclusion", previous.inclusion),
            "exclusion": values.pop("exclusion", previous.exclusion),
            "created_by_account_id": staff_user.id,
        }
        return self.quotation_repo.create(
            quotation_data,
            items=items_data,
            hotels=hotels_data,
            vehicles=vehicles_data,
            itinerary=itinerary_data,
        )

    def update_quotation(
        self,
        quotation_id: uuid.UUID,
        payload: QuotationUpdate,
        staff_user: Account,
    ) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        if quotation.status not in {QuotationStatus.DRAFT, QuotationStatus.REJECTED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quotation can only be updated before it is sent to the customer.",
            )

        values = payload.model_dump(exclude_unset=True)
        items = values.pop("items", None)
        hotels = values.pop("hotels", None)
        vehicles = values.pop("vehicles", None)
        itinerary = values.pop("itinerary", None)

        if items is not None:
            for item in items:
                item["total_price"] = item.get("unit_price", Decimal(0)) * item.get("quantity", 1)
            subtotal = values.get("subtotal")
            if subtotal is None:
                subtotal = sum((Decimal(str(item["unit_price"])) * item["quantity"] for item in items), Decimal(0))
            values["subtotal"] = subtotal
            current_discount = values.get("discount_amount", quotation.discount_amount)
            current_tax = values.get("tax_amount", quotation.tax_amount)
            values["total_amount"] = max(Decimal(0), Decimal(str(subtotal)) - Decimal(str(current_discount)) + Decimal(str(current_tax)))

        if values.get("subtotal") is not None and "total_amount" not in values:
            subtotal = Decimal(str(values["subtotal"]))
            discount = Decimal(str(values.get("discount_amount", quotation.discount_amount)))
            tax = Decimal(str(values.get("tax_amount", quotation.tax_amount)))
            values["total_amount"] = max(Decimal(0), subtotal - discount + tax)

        self.quotation_repo.update(
            quotation,
            values,
            items=[dict(item) for item in items] if items is not None else None,
            hotels=[dict(hotel) for hotel in hotels] if hotels is not None else None,
            vehicles=[dict(vehicle) for vehicle in vehicles] if vehicles is not None else None,
            itinerary=[dict(day) for day in itinerary] if itinerary is not None else None,
        )
        return self.get_quotation(quotation_id)

    def update_quotation_status(self, quotation_id: uuid.UUID, status: QuotationStatus) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        if status == QuotationStatus.SENT:
            quotation.sent_at = datetime.now(timezone.utc)
        elif status == QuotationStatus.ACCEPTED:
            quotation.accepted_at = datetime.now(timezone.utc)
        elif status == QuotationStatus.REJECTED:
            quotation.rejected_at = datetime.now(timezone.utc)
        return self.quotation_repo.update_status(quotation, status)

    def delete_quotation(self, quotation_id: uuid.UUID) -> None:
        self.quotation_repo.delete(self.get_quotation(quotation_id))

    async def generate_quotation_pdf(self, quotation_id: uuid.UUID) -> dict:
        return await generate_and_upload_quotation_pdf(self.get_quotation(quotation_id))

    async def email_quotation(self, quotation_id: uuid.UUID, recipient_email: str) -> str:
        quotation = self.get_quotation(quotation_id)

        uploaded = await generate_and_upload_quotation_pdf(quotation)
        pdf_url = uploaded.get("secure_url") or uploaded.get("url")
        if not pdf_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Quotation PDF upload did not return a download URL.",
            )

        EmailService().send_email(
            recipient_email,
            f"Quotation {quotation.quotation_code} - {quotation.tour_name}",
            (
                f"Dear {quotation.customer.name},\n\n"
                f"Please find your quotation for {quotation.tour_name} at the link below:\n"
                f"{pdf_url}\n\n"
                "This link is hosted in temporary storage and may expire.\n\n"
                "Regards,\nCoochbehar Travels"
            ),
        )
        return pdf_url

    def send_quotation(self, quotation_id: uuid.UUID) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        quotation.sent_at = datetime.now(timezone.utc)
        return self.quotation_repo.update_status(quotation, QuotationStatus.SENT)

    def accept_quotation(self, quotation_id: uuid.UUID, customer: Account) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        if quotation.customer_id and quotation.customer_id != customer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only accept your own quotation.")
        quotation.accepted_at = datetime.now(timezone.utc)
        return self.quotation_repo.update_status(quotation, QuotationStatus.ACCEPTED)

    def reject_quotation(self, quotation_id: uuid.UUID, customer: Account) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        if quotation.customer_id and quotation.customer_id != customer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only reject your own quotation.")
        quotation.rejected_at = datetime.now(timezone.utc)
        return self.quotation_repo.update_status(quotation, QuotationStatus.REJECTED)

    def convert_quotation_to_booking(
        self,
        quotation_id: uuid.UUID,
        staff_user: Account,
        booking_type: str = "PACKAGE",
        notes: str | None = None,
    ) -> Booking:
        from app.repository.booking_repo import BookingRepository

        booking_repo = BookingRepository(self.db)
        quotation = self.get_quotation(quotation_id)
        if quotation.status != QuotationStatus.ACCEPTED:
            # Allow conversion with a note if admin chooses
            pass

        if not quotation.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation must be linked to a customer account before converting to a booking.",
            )

        booking_code = f"BK-{uuid.uuid4().hex[:8].upper()}"
        booking_data = {
            "booking_code": booking_code,
            "customer_id": quotation.customer_id,
            "enquiry_id": quotation.enquiry_id,
            "package_id": getattr(quotation, "package_id", None),
            "variant_id": getattr(quotation, "variant_id", None),
            "booking_type": booking_type,
            "quotation_id": quotation.id,
            "source": BookingSource.OFFLINE,
            "sales_account_id": staff_user.id,
            "status": BookingStatus.CONFIRMED,
            "adult_count": quotation.enquiry.adult_count or 1,
            "child_count": quotation.enquiry.child_count or 0,
            "senior_count": quotation.enquiry.senior_count or 0,
            "subtotal": quotation.subtotal,
            "discount_amount": quotation.discount_amount,
            "total_amount": quotation.total_amount,
            "paid_amount": Decimal(0),
            "due_amount": quotation.total_amount,
            "notes": notes,
            "created_by": staff_user.id,
        }

        booking = booking_repo.create(booking_data)
        return booking
