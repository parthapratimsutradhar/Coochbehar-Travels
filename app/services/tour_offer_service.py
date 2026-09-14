import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import OfferDiscountType, OfferStatus
from app.models.booking import Booking
from app.models.quotation import Quotation
from app.models.tour_offer import TourOffer
from app.models.tour_offer_package import TourOfferPackage
from app.models.tour_offer_usage import TourOfferUsage
from app.repository.tour_offer_repo import TourOfferRepository
from app.schemas.tour_offer import TourOfferCalculationResult, TourOfferCreate, TourOfferUpdate


class TourOfferService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TourOfferRepository(db)

    def create_offer(self, payload: TourOfferCreate) -> TourOffer:
        if payload.valid_until <= payload.valid_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="valid_until must be greater than valid_from.")

        if payload.discount_type == OfferDiscountType.PERCENTAGE and payload.discount_value > Decimal("100"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Percentage discount cannot exceed 100%.")

        offer = TourOffer(
            name=payload.name,
            description=payload.description,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            max_discount_amount=payload.max_discount_amount,
            min_booking_amount=payload.min_booking_amount,
            usage_limit=payload.usage_limit,
            per_customer_limit=payload.per_customer_limit,
            usage_count=0,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            status=payload.status,
        )
        self.db.add(offer)
        self.db.commit()
        self.db.refresh(offer)
        return offer

    def update_offer(self, offer_id: uuid.UUID, payload: TourOfferUpdate) -> TourOffer:
        offer = self.get_offer(offer_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(offer, field, value)

        if offer.valid_until <= offer.valid_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="valid_until must be greater than valid_from.")

        if offer.discount_type == OfferDiscountType.PERCENTAGE and offer.discount_value > Decimal("100"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Percentage discount cannot exceed 100%.")

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def get_offer(self, offer_id: uuid.UUID) -> TourOffer:
        offer = self.repo.get(offer_id)
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found.")
        return offer

    def list_offers(self, *, status: OfferStatus | None = None) -> list[TourOffer]:
        return self.repo.list(status)

    def update_variants(self, offer_id: uuid.UUID, variant_ids: list[uuid.UUID]) -> None:
        offer = self.get_offer(offer_id)
        variants = []
        for variant_id in dict.fromkeys(variant_ids):
            variant = self.repo.get_variant(variant_id)
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Variant {variant_id} not found.",
                )
            variants.append(variant)

        self.db.query(TourOfferPackage).filter(
            TourOfferPackage.offer_id == offer.id
        ).delete()
        for variant in variants:
            self.db.add(TourOfferPackage(offer_id=offer.id, variant_id=variant.id))
        self.db.commit()

    def list_bookings(self, offer_id: uuid.UUID) -> list[Booking]:
        self.get_offer(offer_id)
        return self.repo.list_bookings(offer_id)

    def delete_offer(self, offer_id: uuid.UUID) -> None:
        offer = self.get_offer(offer_id)
        self.db.delete(offer)
        self.db.commit()

    def _get_variant_ids(self, offer_id: uuid.UUID) -> set[uuid.UUID]:
        offer = self.get_offer(offer_id)
        return {link.variant_id for link in offer.package_links}

    def validate_offer(self, *, offer: TourOffer, variant_id: uuid.UUID, booking_amount: Decimal, customer_id: uuid.UUID | None = None) -> None:
        now = datetime.now(timezone.utc)

        if offer.status != OfferStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not active.")

        if not (offer.valid_from <= now < offer.valid_until):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not currently valid.")

        if variant_id not in self._get_variant_ids(offer.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected tour variant is not eligible for this offer.")

        if offer.min_booking_amount is not None and booking_amount < offer.min_booking_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking amount does not meet the minimum booking requirement.")

        if offer.usage_limit is not None and offer.usage_count >= offer.usage_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer usage limit has been reached.")

        if customer_id is not None and offer.per_customer_limit is not None:
            used_count = (
                self.db.query(TourOfferUsage)
                .filter(TourOfferUsage.offer_id == offer.id, TourOfferUsage.customer_id == customer_id)
                .count()
            )
            if used_count >= offer.per_customer_limit:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer usage limit for this offer has been reached.")

    def calculate_discount(self, *, offer: TourOffer, booking_amount: Decimal) -> TourOfferCalculationResult:
        if booking_amount < Decimal(0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking amount cannot be negative.")

        if offer.discount_type == OfferDiscountType.PERCENTAGE:
            calculated_discount = (booking_amount * offer.discount_value) / Decimal("100")
        else:
            calculated_discount = offer.discount_value

        if offer.max_discount_amount is not None:
            applied_discount = min(calculated_discount, offer.max_discount_amount)
        else:
            applied_discount = calculated_discount

        if applied_discount > booking_amount:
            applied_discount = booking_amount

        final_amount = booking_amount - applied_discount

        return TourOfferCalculationResult(
            offer_id=offer.id,
            original_amount=booking_amount,
            discount_type=offer.discount_type,
            discount_value=offer.discount_value,
            calculated_discount=calculated_discount,
            applied_discount=applied_discount,
            final_amount=final_amount,
        )

    def apply_offer(self, *, offer_id: uuid.UUID, variant_id: uuid.UUID, booking_amount: Decimal, customer_id: uuid.UUID | None = None) -> TourOfferCalculationResult:
        offer = self.get_offer(offer_id)
        self.validate_offer(offer=offer, variant_id=variant_id, booking_amount=booking_amount, customer_id=customer_id)
        result = self.calculate_discount(offer=offer, booking_amount=booking_amount)
        return result

    def apply_offer_to_quotation(self, *, quotation: Quotation, offer_id: uuid.UUID) -> Quotation:
        if quotation.variant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation must reference a tour variant before applying an offer.")
        if quotation.customer_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation must reference a customer before applying an offer.")

        result = self.apply_offer(
            offer_id=offer_id,
            variant_id=quotation.variant_id,
            booking_amount=quotation.subtotal,
            customer_id=quotation.customer_id,
        )

        quotation.offer_id = offer_id
        quotation.discount_amount = result.applied_discount
        quotation.total_amount = result.final_amount
        self.db.add(quotation)
        self.consume_offer_usage(
            offer_id=offer_id,
            customer_id=quotation.customer_id,
            quotation_id=quotation.id,
            discount_amount=result.applied_discount,
        )
        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def apply_offer_to_booking(self, *, booking: Booking, offer_id: uuid.UUID) -> Booking:
        if booking.variant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking must reference a tour variant before applying an offer.")

        result = self.apply_offer(
            offer_id=offer_id,
            variant_id=booking.variant_id,
            booking_amount=booking.subtotal,
            customer_id=booking.customer_id,
        )

        booking.offer_id = offer_id
        booking.discount_amount = result.applied_discount
        booking.total_amount = result.final_amount
        booking.due_amount = max(Decimal("0"), result.final_amount - booking.paid_amount)
        self.db.add(booking)
        self.consume_offer_usage(
            offer_id=offer_id,
            customer_id=booking.customer_id,
            booking_id=booking.id,
            discount_amount=result.applied_discount,
        )
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def consume_offer_usage(self, *, offer_id: uuid.UUID, customer_id: uuid.UUID, booking_id: uuid.UUID | None = None, quotation_id: uuid.UUID | None = None, discount_amount: Decimal | None = None) -> TourOfferUsage:
        offer = self.get_offer(offer_id)

        usage = TourOfferUsage(
            offer_id=offer.id,
            customer_id=customer_id,
            booking_id=booking_id,
            quotation_id=quotation_id,
            discount_amount=discount_amount or Decimal("0"),
        )

        offer.usage_count += 1
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def attach_offer_to_booking(self, *, booking: Booking, offer_id: uuid.UUID, discount_amount: Decimal) -> Booking:
        booking.offer_id = offer_id
        booking.discount_amount = discount_amount
        booking.total_amount = max(Decimal("0"), booking.subtotal - discount_amount)
        booking.due_amount = booking.total_amount - booking.paid_amount
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def attach_offer_to_quotation(self, *, quotation: Quotation, offer_id: uuid.UUID, discount_amount: Decimal) -> Quotation:
        quotation.offer_id = offer_id
        quotation.discount_amount = discount_amount
        quotation.total_amount = max(Decimal("0"), quotation.subtotal - discount_amount)
        self.db.add(quotation)
        self.db.commit()
        self.db.refresh(quotation)
        return quotation
