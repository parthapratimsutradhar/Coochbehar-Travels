"""Service layer for tour package business logic.

Orchestrates calls between the repository and the API layer,
applying domain transformations and response formatting.
"""

import math
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.repository.tour_package_repo import TourPackageRepository
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.tour_package import (
    ReviewItemResponse,
    TourPackageDetailResponse,
    TourPackageFilterParams,
    TourPackageListItem,
    TourSeasonResponse,
)


class TourPackageService:
    """Tour package business operations."""

    def __init__(self, db: Session) -> None:
        self.repo = TourPackageRepository(db)

    def list_packages(
        self,
        page: int,
        page_size: int,
        filters: TourPackageFilterParams,
    ) -> PaginatedResponse[TourPackageListItem]:
        """Return a paginated list of tour packages with filters applied."""

        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        results, total_count = self.repo.get_paginated_list(page, page_size, filters)

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        items = []
        for item in results:
            dn = item.get("duration_nights")
            dd = item.get("duration_days")
            if dn is not None and dd is not None:
                item["duration"] = f"{dn}N | {dd}D"
            else:
                item["duration"] = None
            items.append(TourPackageListItem(**item))

        pagination = PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        return PaginatedResponse[TourPackageListItem](
            message="Tour packages fetched successfully",
            data=items,
            pagination=pagination,
        )


    def get_package_by_slug(self, slug: str) -> TourPackageDetailResponse:
        """Fetch full tour package details formatted for consumer frontend."""

        package = self.repo.get_by_slug(slug)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour package with slug '{slug}' not found",
            )
        return self._format_package_detail(package)

    def get_package_by_id(self, package_id: str) -> TourPackageDetailResponse:
        """Fetch full tour package details by id."""

        package = self.repo.get_by_id(package_id)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour package with id '{package_id}' not found",
            )
        return self._format_package_detail(package)

    @classmethod
    def _format_package_detail(cls, package: TourPackage) -> TourPackageDetailResponse:
        """Transform package, package-level reviews, and seasonal variants into structured response."""

        # 1. Package-level reviews
        reviews: list[ReviewItemResponse] = []
        if package.reviews:
            for rev in package.reviews:
                if rev.is_published:
                    reviews.append(ReviewItemResponse.model_validate(rev))

        # 2. Format each season variant
        seasons: list[TourSeasonResponse] = []
        if package.variants:
            for variant in package.variants:
                if not variant.is_active:
                    continue
                season_obj = cls._format_season_variant(variant)
                seasons.append(season_obj)

        return TourPackageDetailResponse(
            id=package.id,
            tour_code=package.tour_code,
            slug=package.slug,
            title=package.title,
            destination=package.destination,
            type=package.type,
            description=package.description,
            is_featured=package.is_featured,
            is_active=package.is_active,
            created_at=package.created_at,
            updated_at=package.updated_at,
            reviews=reviews,
            seasons=seasons,
        )

    @staticmethod
    def _format_season_variant(variant: TourVariant) -> TourSeasonResponse:
        """Format a single seasonal variant with its associated details."""

        duration: str | None = None
        if variant.duration_nights is not None and variant.duration_days is not None:
            duration = f"{variant.duration_nights}N | {variant.duration_days}D"

        key = getattr(variant, "key", None)
        if not key:
            if getattr(variant, "season_type", None):
                key = variant.season_type.lower()
            elif variant.season_name:
                key = variant.season_name.split()[0].lower()

        display_order = getattr(variant, "display_order", None)
        badge = getattr(variant, "badge", None)
        season_type = getattr(variant, "season_type", None)
        currency = getattr(variant, "currency", None) or "INR"
        availability = getattr(variant, "availability", None) or "AVAILABLE"
        price_val = float(variant.base_price) if variant.base_price is not None else 0.0
        starting_price = price_val if price_val > 0 else None

        cover_image: str | None = None
        route: list[Any] = []
        highlights: list[Any] = []
        dates: list[Any] = []
        gallery: list[Any] = []
        itinerary: list[Any] = []
        inclusions: list[Any] = []
        exclusions: list[Any] = []

        details = variant.details
        if details:
            # Banner / cover image
            if isinstance(details.banner, dict):
                cover_image = details.banner.get("cover_image") or details.banner.get("url") or details.banner.get("image")
            elif isinstance(details.banner, str):
                cover_image = details.banner

            # Route stops
            raw_route = details.route_stops
            if isinstance(raw_route, list):
                for i, r in enumerate(raw_route):
                    if isinstance(r, dict):
                        route.append(r)
                    else:
                        route.append({"id": f"r{i+1}", "place": str(r)})

            # Highlights
            raw_hl = details.highlights
            if isinstance(raw_hl, list):
                for i, h in enumerate(raw_hl):
                    if isinstance(h, dict):
                        highlights.append(h)
                    else:
                        highlights.append({"id": f"h{i+1}", "text": str(h)})

            # Departure Dates
            raw_dates = details.departures_dates
            if isinstance(raw_dates, list):
                for i, d in enumerate(raw_dates):
                    if isinstance(d, dict):
                        dates.append(d)
                    else:
                        dates.append({"id": f"d{i+1}", "date": str(d)})

            # Gallery
            raw_gal = details.gallery
            if isinstance(raw_gal, list):
                for i, g in enumerate(raw_gal):
                    if isinstance(g, dict):
                        gallery.append(g)
                    else:
                        gallery.append({"id": f"g{i+1}", "photoId": str(g)})

            # Itinerary
            raw_it = details.itinerary
            if isinstance(raw_it, list):
                for i, item in enumerate(raw_it):
                    if isinstance(item, dict):
                        itinerary.append(item)
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        itinerary.append({"id": f"i{i+1}", "day": str(item[0]), "description": str(item[1])})
                    elif isinstance(item, str):
                        itinerary.append({"id": f"i{i+1}", "day": f"Day {i+1}", "description": item})

            if isinstance(details.inclusions, list):
                inclusions = details.inclusions
            if isinstance(details.exclusions, list):
                exclusions = details.exclusions

        return TourSeasonResponse(
            id=variant.id,
            key=key,
            display_order=display_order,
            slug=variant.slug,
            name=variant.name,
            badge=badge,
            season_type=season_type,
            season_name=variant.season_name,
            cover_image=cover_image,
            valid_from=variant.valid_from,
            valid_to=variant.valid_to,
            duration=duration,
            duration_days=variant.duration_days,
            duration_nights=variant.duration_nights,
            price=price_val,
            currency=currency,
            starting_price=starting_price,
            seats=variant.seats,
            availability=availability,
            is_active=variant.is_active,
            is_default=variant.is_default,
            route=route,
            highlights=highlights,
            dates=dates,
            gallery=gallery,
            itinerary=itinerary,
            inclusions=inclusions,
            exclusions=exclusions,
        )
