import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.hotel import Hotel
from app.models.room import Room


class RoomRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def hotel_exists(self, hotel_id: uuid.UUID) -> bool:
        stmt = select(Hotel.id).where(Hotel.id == hotel_id, Hotel.is_active.is_(True))
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def get_by_id(self, hotel_id: uuid.UUID, room_id: uuid.UUID) -> Room | None:
        stmt = select(Room).where(
            Room.id == room_id,
            Room.hotel_id == hotel_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_rooms(
        self,
        hotel_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        room_type: object | None = None,
        min_price: object | None = None,
        max_price: object | None = None,
        min_capacity: int | None = None,
        max_capacity: int | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[Room], int]:
        stmt = select(Room).where(Room.hotel_id == hotel_id)
        if room_type is not None:
            stmt = stmt.where(Room.room_type == room_type)
        if min_price is not None:
            stmt = stmt.where(Room.price_per_night >= min_price)
        if max_price is not None:
            stmt = stmt.where(Room.price_per_night <= max_price)
        if min_capacity is not None:
            stmt = stmt.where(Room.capacity >= min_capacity)
        if max_capacity is not None:
            stmt = stmt.where(Room.capacity <= max_capacity)
        if is_active is not None:
            stmt = stmt.where(Room.is_active == is_active)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rooms = self.db.execute(
            stmt.order_by(Room.room_number.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return list(rooms), total

    def create(self, **data: object) -> Room:
        room = Room(**data)
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def update(self, room: Room, data: dict[str, object]) -> Room:
        for key, value in data.items():
            setattr(room, key, value)
        self.db.commit()
        self.db.refresh(room)
        return room

    def delete(self, room: Room) -> None:
        room.is_active = False
        self.db.commit()