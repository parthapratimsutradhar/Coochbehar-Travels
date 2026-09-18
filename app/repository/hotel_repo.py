import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.hotel import Hotel


class HotelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, hotel_id: uuid.UUID) -> Hotel | None:
        stmt = (
            select(Hotel)
            .options(joinedload(Hotel.destination_ref))
            .where(Hotel.id == hotel_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def destination_exists(self, destination_id: uuid.UUID) -> bool:
        from app.models.destination import Destination

        stmt = select(Destination.id).where(
            Destination.id == destination_id,
            Destination.is_active.is_(True),
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def list_hotels(
        self,
        page: int = 1,
        page_size: int = 20,
        destination_id: uuid.UUID | None = None,
        category: object | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[Hotel], int]:
        stmt = select(Hotel).options(joinedload(Hotel.destination_ref))
        if destination_id is not None:
            stmt = stmt.where(Hotel.destination_id == destination_id)
        if category is not None:
            stmt = stmt.where(Hotel.category == category)
        if is_active is not None:
            stmt = stmt.where(Hotel.is_active == is_active)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        hotels = self.db.execute(
            stmt.order_by(Hotel.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().scalars().all()
        return list(hotels), total

    def create(self, **data: object) -> Hotel:
        hotel = Hotel(**data)
        self.db.add(hotel)
        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def update(self, hotel: Hotel, data: dict[str, object]) -> Hotel:
        for key, value in data.items():
            setattr(hotel, key, value)
        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def delete(self, hotel: Hotel) -> None:
        hotel.is_active = False
        self.db.commit()
