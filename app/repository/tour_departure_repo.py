import uuid
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.tour_departure import TourDeparture


class TourDepartureRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, departure_id: uuid.UUID) -> TourDeparture | None:
        stmt = select(TourDeparture).where(TourDeparture.id == departure_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_variant(
        self,
        variant_id: uuid.UUID,
        only_upcoming: bool = True,
        only_available: bool = True,
    ) -> list[TourDeparture]:
        stmt = select(TourDeparture).where(TourDeparture.variant_id == variant_id, TourDeparture.is_active.is_(True))
        if only_upcoming:
            stmt = stmt.where(TourDeparture.departure_date >= date.today())
        if only_available:
            stmt = stmt.where(TourDeparture.available_seats > 0)
        stmt = stmt.order_by(TourDeparture.departure_date.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **kwargs) -> TourDeparture:
        departure = TourDeparture(**kwargs)
        self.db.add(departure)
        self.db.commit()
        self.db.refresh(departure)
        return departure

    def update(self, departure: TourDeparture, update_data: dict) -> TourDeparture:
        for k, v in update_data.items():
            if v is not None:
                setattr(departure, k, v)
        self.db.commit()
        self.db.refresh(departure)
        return departure

    def deduct_seats(self, departure: TourDeparture, count: int) -> TourDeparture:
        if departure.available_seats < count:
            raise ValueError("Not enough available seats.")
        departure.available_seats -= count
        self.db.commit()
        self.db.refresh(departure)
        return departure

    def restore_seats(self, departure: TourDeparture, count: int) -> TourDeparture:
        departure.available_seats = min(departure.total_seats, departure.available_seats + count)
        self.db.commit()
        self.db.refresh(departure)
        return departure
