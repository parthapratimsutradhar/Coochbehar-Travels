import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.hotel import Hotel
from app.repository.hotel_repo import HotelRepository
from app.schemas.hotel import HotelCreate, HotelUpdate


class HotelService:
    def __init__(self, db: Session) -> None:
        self.repo = HotelRepository(db)

    def list_hotels(
        self,
        page: int = 1,
        page_size: int = 20,
        destination_id: uuid.UUID | None = None,
        category: object | None = None,
        is_active: bool | None = True,
    ) -> dict:
        items, total = self.repo.list_hotels(
            page=page,
            page_size=page_size,
            destination_id=destination_id,
            category=category,
            is_active=is_active,
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    def get_hotel(self, hotel_id: uuid.UUID) -> Hotel:
        hotel = self.repo.get_by_id(hotel_id)
        if not hotel or not hotel.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
        return hotel

    def _validate_destination(self, destination_id: uuid.UUID | None) -> None:
        if destination_id and not self.repo.destination_exists(destination_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")

    def create_hotel(self, payload: HotelCreate) -> Hotel:
        self._validate_destination(payload.destination_id)
        return self.repo.create(**payload.model_dump())

    def update_hotel(self, hotel_id: uuid.UUID, payload: HotelUpdate) -> Hotel:
        hotel = self.get_hotel(hotel_id)
        data = payload.model_dump(exclude_unset=True)
        self._validate_destination(data.get("destination_id"))
        return self.repo.update(hotel, data)

    def delete_hotel(self, hotel_id: uuid.UUID) -> None:
        hotel = self.get_hotel(hotel_id)
        self.repo.delete(hotel)
