import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.destination import Destination
from app.models.hotel import Hotel
from app.models.tour_package import TourPackage


class DestinationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, destination_id: uuid.UUID) -> Destination | None:
        stmt = select(Destination).where(Destination.id == destination_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Destination | None:
        stmt = select(Destination).where(Destination.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

    def has_tour_packages(self, destination_id: uuid.UUID) -> bool:
        stmt = select(TourPackage.id).where(TourPackage.destination_id == destination_id).exists()
        return self.db.query(stmt).scalar()

    def has_hotels(self, destination_id: uuid.UUID) -> bool:
        stmt = select(Hotel.id).where(Hotel.destination_id == destination_id).exists()
        return self.db.query(stmt).scalar()

    def get_usage_counts(self, destination_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        counts = {
            destination_id: {"tour_package_count": 0, "hotel_count": 0}
            for destination_id in destination_ids
        }
        if not destination_ids:
            return counts

        package_counts = (
            self.db.query(TourPackage.destination_id, func.count(TourPackage.id))
            .filter(TourPackage.destination_id.in_(destination_ids))
            .group_by(TourPackage.destination_id)
            .all()
        )
        hotel_counts = (
            self.db.query(Hotel.destination_id, func.count(Hotel.id))
            .filter(Hotel.destination_id.in_(destination_ids))
            .group_by(Hotel.destination_id)
            .all()
        )
        for destination_id, count in package_counts:
            counts[destination_id]["tour_package_count"] = count
        for destination_id, count in hotel_counts:
            counts[destination_id]["hotel_count"] = count
        return counts

    def transfer_usage(
        self,
        source_destination_id: uuid.UUID,
        target_destination_id: uuid.UUID,
    ) -> tuple[int, int]:
        try:
            package_count = (
                self.db.query(TourPackage)
                .filter(TourPackage.destination_id == source_destination_id)
                .update(
                    {TourPackage.destination_id: target_destination_id},
                    synchronize_session=False,
                )
            )
            hotel_count = (
                self.db.query(Hotel)
                .filter(Hotel.destination_id == source_destination_id)
                .update(
                    {Hotel.destination_id: target_destination_id},
                    synchronize_session=False,
                )
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return package_count, hotel_count

    def create(self, **kwargs) -> Destination:
        destination = Destination(**kwargs)
        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def list_destinations(
        self,
        page: int = 1,
        page_size: int = 20,
        is_domestic: bool | None = None,
        is_featured: bool | None = None,
        is_active: bool | None = True,
        search: str | None = None,
    ) -> tuple[list[Destination], int]:
        stmt = select(Destination)
        if is_active is not None:
            stmt = stmt.where(Destination.is_active == is_active)
        if is_domestic is not None:
            stmt = stmt.where(Destination.is_domestic == is_domestic)
        if is_featured is not None:
            stmt = stmt.where(Destination.is_featured == is_featured)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Destination.name.ilike(term)
                | Destination.slug.ilike(term)
                | Destination.country.ilike(term)
            )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        destinations = self.db.execute(
            stmt.order_by(Destination.name.asc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(destinations), total

    def update(self, destination: Destination, update_data: dict) -> Destination:
        for k, v in update_data.items():
            if v is not None:
                setattr(destination, k, v)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def delete(self, destination: Destination) -> None:
        destination.is_active = False
        self.db.commit()
        self.db.refresh(destination)
