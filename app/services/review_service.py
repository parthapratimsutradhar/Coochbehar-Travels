import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.messages.error import ReviewError
from app.models.account import Account
from app.models.review import Review
from app.models.tour_package import TourPackage
from app.repository.customer_repo import CustomerRepository
from app.repository.review_repo import ReviewRepository
from app.repository.tour_package_repo import TourPackageRepository
from app.schemas.review import AdminReviewCreate, AdminReviewUpdate
from app.services.cloudinary_service import promote_cloudinary_asset


async def _promote_gallery(gallery_items: list[Any] | None) -> list[dict[str, Any]]:
    promoted_items: list[dict[str, Any]] = []
    for item in gallery_items or []:
        item_dict = (
            item.model_dump()
            if hasattr(item, "model_dump")
            else (item if isinstance(item, dict) else {"url": str(item)})
        )
        url = item_dict.get("url")
        item_dict["id"] = str(uuid.uuid4())
        if url:
            media_type = item_dict.get("type") or "image"
            promoted = await promote_cloudinary_asset(
                url,
                "review-gallery",
                resource_type=media_type,
            )
            item_dict["url"] = promoted["url"]
        promoted_items.append(item_dict)
    return promoted_items


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReviewRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.package_repo = TourPackageRepository(db)

    def get_package(self, package_id: uuid.UUID) -> TourPackage:
        package = self.package_repo.get_by_id(package_id)
        if not package or not package.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")
        return package

    def get_review(self, review_id: uuid.UUID) -> Review:
        review = self.repo.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ReviewError.REVIEW_NOT_FOUND)
        return review

    def list_reviews(
        self,
        package_id: uuid.UUID,
        page: int,
        page_size: int,
        is_verified: bool | None = None,
        is_published: bool | None = None,
    ) -> dict:
        self.get_package(package_id)
        items, total = self.repo.list_for_package(
            package_id,
            page,
            page_size,
            is_verified=is_verified,
            is_published=is_published,
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    async def create_review(self, package_id: uuid.UUID, payload: AdminReviewCreate) -> Review:
        self.get_package(package_id)
        customer: Account | None = None
        if payload.customer_id:
            customer = self.customer_repo.get_by_id(payload.customer_id)
            if not customer or not customer.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ReviewError.CUSTOMER_NOT_FOUND)

        name = customer.name if customer else (payload.name or "Anonymous Traveler")
        return self.repo.create(
            package_id=package_id,
            customer_id=customer.id if customer else None,
            name=name,
            rating=payload.rating,
            review=payload.review,
            review_gallery=await _promote_gallery(payload.review_gallery),
            is_verified=customer is not None,
            is_published=payload.is_published,
        )

    async def update_review(self, review_id: uuid.UUID, payload: AdminReviewUpdate) -> Review:
        review = self.get_review(review_id)
        data = payload.model_dump(exclude_unset=True)

        if "customer_id" in data:
            customer = None
            if data["customer_id"]:
                customer = self.customer_repo.get_by_id(data["customer_id"])
                if not customer or not customer.is_active:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ReviewError.CUSTOMER_NOT_FOUND)
            data["name"] = customer.name if customer else data.get("name") or review.name
            data["is_verified"] = customer is not None
        elif "name" not in data and review.customer_id:
            data.pop("name", None)
            data["is_verified"] = True
        else:
            data["is_verified"] = review.customer_id is not None

        if "review_gallery" in data and data["review_gallery"] is not None:
            data["review_gallery"] = await _promote_gallery(data["review_gallery"])
        return self.repo.update(review, data)

    def delete_review(self, review_id: uuid.UUID) -> None:
        self.repo.delete(self.get_review(review_id))
