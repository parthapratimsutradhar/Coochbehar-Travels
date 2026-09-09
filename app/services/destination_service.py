import uuid
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.destination import Destination
from app.repository.destination_repo import DestinationRepository
from app.schemas.destination import DestinationCreate, DestinationUpdate


class DestinationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DestinationRepository(db)

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[\s_-]+", "-", text)

    def list_destinations(
        self,
        page: int = 1,
        page_size: int = 20,
        is_domestic: bool | None = None,
        is_featured: bool | None = None,
        is_popular: bool | None = None,
        is_active: bool | None = True,
        search: str | None = None,
    ) -> dict:
        items, total = self.repo.list_destinations(
            page=page,
            page_size=page_size,
            is_domestic=is_domestic,
            is_featured=is_featured,
            is_popular=is_popular,
            is_active=is_active,
            search=search,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        }

    def get_destination(self, destination_id: uuid.UUID) -> Destination:
        dest = self.repo.get_by_id(destination_id)
        if not dest or not dest.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
        return dest

    def get_by_slug(self, slug: str) -> Destination:
        dest = self.repo.get_by_slug(slug)
        if not dest or not dest.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
        return dest

    def create_destination(self, payload: DestinationCreate) -> Destination:
        slug = payload.slug or self._slugify(payload.name)
        existing = self.repo.get_by_slug(slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A destination with this slug already exists.",
            )
        data = payload.model_dump()
        data["slug"] = slug
        return self.repo.create(**data)

    def update_destination(self, destination_id: uuid.UUID, payload: DestinationUpdate) -> Destination:
        dest = self.get_destination(destination_id)
        data = payload.model_dump(exclude_unset=True)
        if "slug" in data and data["slug"] is not None:
            existing = self.repo.get_by_slug(data["slug"])
            if existing and existing.id != destination_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A destination with this slug already exists.",
                )
        return self.repo.update(dest, data)

    def delete_destination(self, destination_id: uuid.UUID) -> None:
        dest = self.get_destination(destination_id)
        self.repo.delete(dest)
