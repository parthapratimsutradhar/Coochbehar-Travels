import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import TourType
from app.core.messages.error import PackageError, WishlistError
from app.core.messages.success import WishlistSuccess
from app.repository.wishlist_repo import WishlistRepository
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.wishlist import WishlistItemResponse
from app.services.tour_package_service import TourPackageService


class WishlistService:
    """Customer wishlist operations and response formatting."""

    def __init__(self, db: Session) -> None:
        self.repo = WishlistRepository(db)
        self.package_service = TourPackageService(db)

    def list_wishlist(
        self,
        customer_id: uuid.UUID,
        page: int,
        page_size: int,
        destination: str | None = None,
        tour_type: TourType | None = None,
        season: str | None = None,
        is_featured: bool | None = None,
        search: str | None = None,
        sort_order: str = "desc",
    ) -> PaginatedResponse[WishlistItemResponse]:
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        rows, total_items = self.repo.list_for_customer(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
            destination=destination,
            tour_type=tour_type,
            season=season,
            is_featured=is_featured,
            search=search,
            sort_order=sort_order,
        )
        items = []
        for wishlist, package in rows:
            package_item = self.package_service.build_wishlist_package_item(package)
            items.append(
                WishlistItemResponse(
                    id=wishlist.id,
                    package_id=package.id,
                    tour_code=package_item.tour_code,
                    slug=package_item.slug,
                    title=package_item.title,
                    destination=package_item.destination_name,
                    type=package_item.type,
                    description=package_item.description,
                    season_name=package_item.season_name,
                    badge=package_item.badge,
                    banner=package_item.banner,
                    is_featured=package_item.is_featured,
                    wishlisted_at=wishlist.created_at,
                )
            )

        total_pages = math.ceil(total_items / page_size) if total_items else 0
        return PaginatedResponse(
            message=WishlistSuccess.RETRIEVED,
            data=items,
            pagination=PaginationMeta(
                current_page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )

    def add_to_wishlist(self, customer_id: uuid.UUID, package_slug: str) -> None:
        package = self.repo.get_active_package_by_slug(package_slug)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )
        if self.repo.get_customer_entry(customer_id, package.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=WishlistError.ALREADY_EXISTS,
            )
        self.repo.add(customer_id, package.id)

    def remove_from_wishlist(self, customer_id: uuid.UUID, package_slug: str) -> None:
        wishlist = self.repo.get_customer_entry_by_slug(customer_id, package_slug)
        if wishlist is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=WishlistError.NOT_FOUND,
            )
        self.repo.delete(wishlist)