import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.destination import Destination


class DestinationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, destination_id: uuid.UUID) -> Destination | None:
        stmt = select(Destination).where(Destination.id == destination_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Destination | None:
        stmt = select(Destination).where(Destination.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

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
        is_popular: bool | None = None,
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
        if is_popular is not None:
            stmt = stmt.where(Destination.is_popular == is_popular)
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
