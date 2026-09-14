import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import OfferStatus
from app.models.booking import Booking
from app.models.tour_offer import TourOffer
from app.models.tour_variant import TourVariant


class TourOfferRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, offer_id: uuid.UUID) -> TourOffer | None:
        stmt = (
            select(TourOffer)
            .options(selectinload(TourOffer.package_links))
            .where(TourOffer.id == offer_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, offer_status: OfferStatus | None = None) -> list[TourOffer]:
        stmt = select(TourOffer).options(selectinload(TourOffer.package_links))
        if offer_status is not None:
            stmt = stmt.where(TourOffer.status == offer_status)
        return list(
            self.db.execute(stmt.order_by(TourOffer.created_at.desc())).scalars().all()
        )

    def get_variant(self, variant_id: uuid.UUID) -> TourVariant | None:
        return self.db.get(TourVariant, variant_id)

    def list_bookings(self, offer_id: uuid.UUID) -> list[Booking]:
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.customer),
                selectinload(Booking.travellers),
                selectinload(Booking.status_history),
            )
            .where(Booking.offer_id == offer_id)
            .order_by(Booking.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())
