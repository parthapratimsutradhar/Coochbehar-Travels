import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.messages.error import RoomError
from app.models.room import Room
from app.repository.room_repo import RoomRepository
from app.schemas.room import RoomCreate, RoomUpdate


class RoomService:
    def __init__(self, db: Session) -> None:
        self.repo = RoomRepository(db)

    def _validate_hotel(self, hotel_id: uuid.UUID) -> None:
        if not self.repo.hotel_exists(hotel_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RoomError.HOTEL_NOT_FOUND)

    def get_room(self, hotel_id: uuid.UUID, room_id: uuid.UUID) -> Room:
        room = self.repo.get_by_id(hotel_id, room_id)
        if not room or not room.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RoomError.ROOM_NOT_FOUND)
        return room

    def create_room(self, hotel_id: uuid.UUID, payload: RoomCreate) -> Room:
        self._validate_hotel(hotel_id)
        return self.repo.create(hotel_id=hotel_id, **payload.model_dump())

    def update_room(
        self,
        hotel_id: uuid.UUID,
        room_id: uuid.UUID,
        payload: RoomUpdate,
    ) -> Room:
        room = self.get_room(hotel_id, room_id)
        return self.repo.update(room, payload.model_dump(exclude_unset=True))

    def delete_room(self, hotel_id: uuid.UUID, room_id: uuid.UUID) -> None:
        room = self.get_room(hotel_id, room_id)
        self.repo.delete(room)

    def list_rooms(
        self,
        hotel_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        room_type: object | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        min_capacity: int | None = None,
        max_capacity: int | None = None,
        is_active: bool | None = True,
    ) -> dict:
        self._validate_hotel(hotel_id)
        items, total = self.repo.list_rooms(
            hotel_id=hotel_id,
            page=page,
            page_size=page_size,
            room_type=room_type,
            min_price=min_price,
            max_price=max_price,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            is_active=is_active,
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }