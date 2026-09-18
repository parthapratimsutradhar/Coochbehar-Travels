from datetime import datetime, timezone
from decimal import Decimal
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import BookingSource, BookingStatus, EnquiryStatus, QuotationStatus
from app.models.account import Account
from app.models.booking import Booking
from app.models.quotation import Quotation
from app.repository.booking_repo import BookingRepository
from app.repository.enquiry_repo import EnquiryRepository
from app.repository.quotation_repo import QuotationRepository
from app.schemas.quotation import QuotationCreate, QuotationUpdate


class QuotationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quotation_repo = QuotationRepository(db)
        self.enquiry_repo = EnquiryRepository(db)
        self.booking_repo = BookingRepository(db)

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
            "hotel_id": payload.hotel_id,
            "room_id": payload.room_id,
            "vehicle_id": payload.vehicle_id,
            "tour_name": payload.tour_name,
            "travel_date": payload.travel_date,
            "return_date": payload.return_date,
            "adult_count": payload.adult_count,
            "child_count": payload.child_count,
            "senior_count": payload.senior_count,
            "room_count": payload.room_count,
            "vehicle_count": payload.vehicle_count,
            "meal_plan": payload.meal_plan,
            "subtotal": subtotal,
            "discount_amount": payload.discount_amount,
            "tax_amount": payload.tax_amount,
            "total_amount": total_amount,
            "valid_until": payload.valid_until,
            "status": QuotationStatus.DRAFT,
            "terms_and_conditions": payload.terms_and_conditions,
            "created_by_account_id": staff_user.id,
        }

        quotation = self.quotation_repo.create(quotation_data, items=items_data)

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

    def update_quotation(self, quotation_id: uuid.UUID, payload: QuotationUpdate) -> Quotation:
        quotation = self.get_quotation(quotation_id)
        update_data = payload.model_dump(exclude_unset=True)
        items_data = [it.model_dump() for it in payload.items] if payload.items is not None else None

        # Recompute totals if items updated
        if items_data is not None:
            subtotal = sum((it["unit_price"] * it["quantity"] for it in items_data), Decimal(0))
            disc = update_data.get("discount_amount", quotation.discount_amount)
            tax = update_data.get("tax_amount", quotation.tax_amount)
            update_data["subtotal"] = subtotal
            update_data["total_amount"] = max(Decimal(0), subtotal - disc + tax)

        return self.quotation_repo.update(quotation, update_data, items=items_data)

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
            "package_id": quotation.package_id,
            "variant_id": quotation.variant_id,
            "booking_type": booking_type,
            "quotation_id": quotation.id,
            "source": BookingSource.OFFLINE,
            "sales_account_id": staff_user.id,
            "status": BookingStatus.CONFIRMED,
            "adult_count": quotation.adult_count,
            "child_count": quotation.child_count,
            "senior_count": quotation.senior_count,
            "subtotal": quotation.subtotal,
            "discount_amount": quotation.discount_amount,
            "total_amount": quotation.total_amount,
            "paid_amount": Decimal(0),
            "due_amount": quotation.total_amount,
            "notes": notes,
            "created_by": staff_user.id,
        }

        # Convert quotation items to booking costs
        costs_data = []
        for it in quotation.items:
            costs_data.append({
                "cost_type": it.item_type.value,
                "description": f"{it.name}: {it.description}" if it.description else it.name,
                "estimated_amount": it.total_price,
                "actual_amount": it.total_price,
                "paid_amount": Decimal(0),
                "due_amount": it.total_price,
                "status": "PENDING",
            })

        booking = self.booking_repo.create(booking_data, costs=costs_data)
        return booking
