import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.hotel import Hotel
from app.repository.hotel_repo import HotelRepository
from app.schemas.hotel import HotelCreate, HotelUpdate
from app.services.cloudinary_service import promote_cloudinary_asset


async def _promote_hotel_images(image_items: list[Any]) -> list[dict[str, Any]]:
    promoted_items: list[dict[str, Any]] = []
    for item in image_items:
        item_dict = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        item_dict.setdefault("id", str(uuid.uuid4()))
        if item_dict.get("url"):
            promoted = await promote_cloudinary_asset(
                item_dict["url"],
                "hotel-images",
                resource_type=item_dict.get("type") or "image",
            )
            item_dict["url"] = promoted["url"]
        promoted_items.append(item_dict)
    return promoted_items


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

    async def create_hotel(self, payload: HotelCreate) -> Hotel:
        self._validate_destination(payload.destination_id)
        data = payload.model_dump()
        data["image"] = await _promote_hotel_images(data["image"])
        return self.repo.create(**data)

    async def update_hotel(self, hotel_id: uuid.UUID, payload: HotelUpdate) -> Hotel:
        hotel = self.get_hotel(hotel_id)
        data = payload.model_dump(exclude_unset=True)
        self._validate_destination(data.get("destination_id"))
        if "image" in data:
            data["image"] = await _promote_hotel_images(data["image"])
        return self.repo.update(hotel, data)

    def delete_hotel(self, hotel_id: uuid.UUID) -> None:
        hotel = self.get_hotel(hotel_id)
        self.repo.delete(hotel)
