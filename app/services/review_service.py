import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, EnquiryStatus
from app.core.messages.error import PackageError, ReviewError
from app.models.account import Account
from app.models.review import Review
from app.models.tour_package import TourPackage
from app.repository.customer_repo import CustomerRepository
from app.repository.review_repo import ReviewRepository
from app.repository.tour_package_repo import TourPackageRepository
from app.schemas.review import (
    AdminReviewCreate,
    AdminReviewUpdate,
    ReviewCreate,
    ReviewEligibilityResponse,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.tour_package import ReviewItemResponse
from app.services.cdn_service import promote_cdn_asset
from app.services.notification_service import NotificationService


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
            promoted = await promote_cdn_asset(
                url,
                "review-gallery",
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )
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

    def list_published_reviews(
        self,
        package_slug: str,
        page: int,
        page_size: int,
    ) -> dict:
        package = None
        try:
            package = self.package_repo.get_by_id(uuid.UUID(package_slug))
        except ValueError:
            pass
        if package is None:
            package = self.package_repo.get_by_slug(package_slug)
        if package is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)
        reviews, total = self.repo.list_published_for_package(package.id, page, page_size)
        return {
            "items": [
                ReviewItemResponse(
                    id=review.id,
                    reviewer_by=review.customer.name if review.customer else review.name,
                    reviewer_pic=review.customer.profile_pic if review.customer else None,
                    name=review.name,
                    rating=review.rating,
                    review=review.review,
                    review_gallery=review.review_gallery or [],
                    created_at=review.created_at,
                )
                for review in reviews
            ],
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    def get_customer_eligibility(
        self,
        package_slug: str,
        customer_id: uuid.UUID,
    ) -> ReviewEligibilityResponse:
        package = self.package_repo.get_by_slug(package_slug)
        if package is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)

        review = self.repo.get_customer_review(customer_id, package.id)
        has_reviewed = review is not None
        can_review = self.repo.has_eligible_enquiry(
            customer_id,
            package.id,
            date.today(),
        ) or self.repo.has_completed_customer_tour(customer_id, package.id)
        return ReviewEligibilityResponse(
            package_id=package.id,
            can_review=can_review and not has_reviewed,
            has_reviewed=has_reviewed,
            review=ReviewResponse.model_validate(review) if review else None,
        )

    async def create_customer_review(self, customer: Account, payload: ReviewCreate) -> None:
        package = self.package_repo.get_by_id(payload.package_id)
        if package is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)

        can_review = self.repo.has_eligible_enquiry(
            customer.id,
            payload.package_id,
            date.today(),
        ) or self.repo.has_completed_customer_tour(customer.id, payload.package_id)
        if not can_review:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ReviewError.TOUR_NOT_COMPLETED,
            )

        if self.repo.has_customer_review(customer.id, payload.package_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ReviewError.ALREADY_REVIEWED,
            )

        review = self.repo.create(
            package_id=payload.package_id,
            customer_id=customer.id,
            name=customer.name,
            rating=payload.rating,
            review=payload.review,
            review_gallery=await _promote_gallery(payload.review_gallery),
            is_verified=True,
            is_published=True,
        )
        review_date = review.created_at.isoformat() if review.created_at else None
        service = NotificationService(self.db)
        await service.notify_admins(
            notification_type="REVIEW_SUBMITTED",
            title="New tour review",
            message=f"{customer.name} reviewed {package.title} with a rating of {payload.rating}/5 on {review_date}.",
            data={
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "tour_name": package.title,
                "rating": payload.rating,
                "review_id": str(review.id),
                "review_date": review_date,
            },
        )
        await service.notify_customer(
            customer.id,
            notification_type="REVIEW_PUBLISHED",
            title="Thank you for your review",
            message=f"Thank you for reviewing {package.title}. You gave it a rating of {payload.rating}/5.",
            data={"tour_name": package.title, "rating": payload.rating, "review_id": str(review.id)},
        )

    async def update_customer_review(
        self,
        review_id: uuid.UUID,
        customer_id: uuid.UUID,
        payload: ReviewUpdate,
    ) -> Review:
        review = self.repo.get_customer_owned_review(review_id, customer_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ReviewError.REVIEW_NOT_FOUND,
            )
        update_data = payload.model_dump(exclude_unset=True)
        if "review_gallery" in update_data and update_data["review_gallery"] is not None:
            update_data["review_gallery"] = await _promote_gallery(update_data["review_gallery"])
        return self.repo.update(review, update_data)

    def delete_customer_review(self, review_id: uuid.UUID, customer_id: uuid.UUID) -> None:
        review = self.repo.get_customer_owned_review(review_id, customer_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ReviewError.REVIEW_NOT_FOUND,
            )
        self.repo.delete(review)

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
