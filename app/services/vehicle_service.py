import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.messages.error import VehicleError
from app.models.vehicle import Vehicle
from app.repository.vehicle_repo import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


class VehicleService:
    def __init__(self, db: Session) -> None:
        self.repo = VehicleRepository(db)

    def get_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = self.repo.get_by_id(vehicle_id)
        if not vehicle or not vehicle.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=VehicleError.VEHICLE_NOT_FOUND)
        return vehicle

    def create_vehicle(self, payload: VehicleCreate) -> Vehicle:
        return self.repo.create(**payload.model_dump())

    def update_vehicle(self, vehicle_id: uuid.UUID, payload: VehicleUpdate) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)
        return self.repo.update(vehicle, payload.model_dump(exclude_unset=True))

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