import uuid
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.destination import Destination
from app.repository.destination_repo import DestinationRepository
from app.schemas.destination import (
    DestinationBulkTransferRequest,
    DestinationBulkTransferResponse,
    DestinationCreate,
    DestinationUpdate,
)
from app.services.cdn_service import promote_cdn_asset


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
        is_active: bool | None = True,
        search: str | None = None,
    ) -> dict:
        items, total = self.repo.list_destinations(
            page=page,
            page_size=page_size,
            is_domestic=is_domestic,
            is_featured=is_featured,
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

    def get_usage_counts(self, destination_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        return self.repo.get_usage_counts(destination_ids)

    def bulk_transfer(
        self,
        payload: DestinationBulkTransferRequest,
    ) -> DestinationBulkTransferResponse:
        if payload.source_destination_id == payload.target_destination_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and target destinations must be different.",
            )

        self.get_destination(payload.source_destination_id)
        self.get_destination(payload.target_destination_id)
        package_count, hotel_count = self.repo.transfer_usage(
            payload.source_destination_id,
            payload.target_destination_id,
        )
        return DestinationBulkTransferResponse(
            source_destination_id=payload.source_destination_id,
            target_destination_id=payload.target_destination_id,
            tour_packages_transferred=package_count,
            hotels_transferred=hotel_count,
        )

    async def create_destination(self, payload: DestinationCreate) -> Destination:
        slug = payload.slug or self._slugify(payload.name)
        existing = self.repo.get_by_slug(slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A destination with this slug already exists.",
            )
        data = payload.model_dump()
        data["slug"] = slug
        if data.get("image_url"):
            promoted = await promote_cdn_asset(data["image_url"], "destination-images")
            data["image_url"] = promoted["url"]
        return self.repo.create(**data)

    async def update_destination(self, destination_id: uuid.UUID, payload: DestinationUpdate) -> Destination:
        dest = self.repo.get_by_id(destination_id)
        if dest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")
        data = payload.model_dump(exclude_unset=True)
        if "slug" in data and data["slug"] is not None:
            existing = self.repo.get_by_slug(data["slug"])
            if existing and existing.id != destination_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A destination with this slug already exists.",
                )
        if "image_url" in data and data["image_url"]:
            promoted = await promote_cdn_asset(data["image_url"], "destination-images")
            data["image_url"] = promoted["url"]
        return self.repo.update(dest, data)

    def delete_destination(self, destination_id: uuid.UUID) -> None:
        dest = self.get_destination(destination_id)
        if self.repo.has_tour_packages(dest.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a destination that is used by tour packages.",
            )
        if self.repo.has_hotels(dest.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a destination that is used by hotels.",
            )
        self.repo.delete(dest)
