import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.messages.error import VehicleError
from app.models.vehicle import Vehicle
from app.repository.vehicle_repo import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.cloudinary_service import promote_cloudinary_asset


async def _promote_vehicle_images(image_items: list[Any]) -> list[dict[str, Any]]:
    promoted_items: list[dict[str, Any]] = []
    for item in image_items:
        item_dict = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        item_dict.setdefault("id", str(uuid.uuid4()))
        if item_dict.get("url"):
            promoted = await promote_cloudinary_asset(
                item_dict["url"],
                "vehicle-images",
                resource_type=item_dict.get("type") or "image",
            )
            item_dict["url"] = promoted["url"]
        promoted_items.append(item_dict)
    return promoted_items


class VehicleService:
    def __init__(self, db: Session) -> None:
        self.repo = VehicleRepository(db)

    def get_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.repo.get_by_id(vehicle_id)
        if not vehicle or not vehicle.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=VehicleError.VEHICLE_NOT_FOUND)
        return vehicle

    async def create_vehicle(self, payload: VehicleCreate) -> Vehicle:
        data = payload.model_dump()
        data["vehicle_image"] = await _promote_vehicle_images(data["vehicle_image"])
        return self.repo.create(**data)

    async def update_vehicle(self, vehicle_id: uuid.UUID, payload: VehicleUpdate) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)
        data = payload.model_dump(exclude_unset=True)
        if "vehicle_image" in data:
            data["vehicle_image"] = await _promote_vehicle_images(data["vehicle_image"])
        return self.repo.update(vehicle, data)

    def delete_vehicle(self, vehicle_id: uuid.UUID) -> None:
        vehicle = self.get_vehicle(vehicle_id)
        self.repo.delete(vehicle)

    def list_vehicles(
        self,
        page: int = 1,
        page_size: int = 20,
        vehicle_type: object | None = None,
        search: str | None = None,
        is_active: bool | None = True,
    ) -> dict:
        items, total = self.repo.list_vehicles(
            page=page,
            page_size=page_size,
            vehicle_type=vehicle_type,
            search=search,
            is_active=is_active,
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }