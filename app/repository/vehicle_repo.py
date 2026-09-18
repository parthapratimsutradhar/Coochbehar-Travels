import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle


class VehicleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id)
        ).scalar_one_or_none()

    def list_vehicles(
        self,
        page: int = 1,
        page_size: int = 20,
        vehicle_type: object | None = None,
        search: str | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[Vehicle], int]:
        stmt = select(Vehicle)
        if vehicle_type is not None:
            stmt = stmt.where(Vehicle.vehicle_type == vehicle_type)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Vehicle.name.ilike(term)
                | Vehicle.registration_number.ilike(term)
            )
        if is_active is not None:
            stmt = stmt.where(Vehicle.is_active == is_active)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        vehicles = self.db.execute(
            stmt.order_by(Vehicle.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return list(vehicles), total

    def create(self, **data: object) -> Vehicle:
        vehicle = Vehicle(**data)
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def update(self, vehicle: Vehicle, data: dict[str, object]) -> Vehicle:
        for key, value in data.items():
            setattr(vehicle, key, value)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def delete(self, vehicle: Vehicle) -> None:
        vehicle.is_active = False
        self.db.commit()