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
from app.core.messages.error import PackageError
from app.repository.tour_package_repo import TourPackageRepository
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.tour_package import (
    TourPackageDetailResponse,
    TourPackageFilterParams,
    TourPackageListItem,
    TourPackageSelectionItem,
    TourPackageSelectionVariant,
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
        customer_id=None,
    ) -> PaginatedResponse[TourPackageListItem]:
        """Return a paginated list of tour packages with filters applied."""

        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        results, total_count = self.repo.get_paginated_list(page, page_size, filters)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        items = []
        for item in results:
            package = self.repo.get_by_id(item["id"])
            default_variant = self._get_default_variant(package)

            item["season_name"] = default_variant.season_name if default_variant else None
            item["badge"] = default_variant.badge if default_variant else None
            item["banner"] = self._extract_banner_media(default_variant.details) if default_variant and default_variant.details else None

            dn = item.get("duration_nights")
            dd = item.get("duration_days")
            if dn is not None and dd is not None:
                item["duration"] = f"{dn}N | {dd}D"
            else:
                item["duration"] = None

                item["is_wishlist"] = bool(
                    customer_id and self.repo.is_wishlisted(item["id"], customer_id)
                )

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
            message="Items fetched successfully",
            data=items,
            pagination=pagination,
        )

    def list_packages_for_selection(
        self,
        search: str | None = None,
    ) -> list[TourPackageSelectionItem]:
        """Return the compact active-package payload used by selectors."""

        packages = self.repo.get_active_for_selection(search=search, limit=5)
        items = []
        for package in packages:
            active_variants = [variant for variant in package.variants if variant.is_active]
            default_variant = self._get_default_variant(package)
            banner = (
                self._extract_banner_media(default_variant.details)
                if default_variant and default_variant.details
                else None
            )
            items.append(
                TourPackageSelectionItem(
                    id=package.id,
                    title=package.title,
                    banner=banner,
                    variants=[
                        TourPackageSelectionVariant(
                            id=variant.id,
                            name=variant.name,
                            season_name=variant.season_name,
                        )
                        for variant in active_variants
                    ],
                )
            )
        return items

    def get_package_for_selection(self, slug: str) -> TourPackageSelectionItem:
        """Return one active package with its active variants for selection."""

        package = self.repo.get_by_slug(slug, active_only=True)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )

        active_variants = [variant for variant in package.variants if variant.is_active]
        if not active_variants:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )

        default_variant = self._get_default_variant(package)
        banner = (
            self._extract_banner_media(default_variant.details)
            if default_variant and default_variant.details
            else None
        )
        return TourPackageSelectionItem(
            id=package.id,
            title=package.title,
            banner=banner,
            variants=[
                TourPackageSelectionVariant(
                    id=variant.id,
                    name=variant.name,
                    season_name=variant.season_name,
                )
                for variant in active_variants
            ],
        )

    def get_package_by_slug(self, slug: str, customer_id=None) -> TourPackageDetailResponse:
        """Fetch full tour package details formatted for consumer frontend."""

        package = self.repo.get_by_slug(slug, active_only=True)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )
        return self._format_package_detail(
            package,
            is_wishlist=bool(customer_id and self.repo.is_wishlisted(package.id, customer_id)),
        )

    def get_package_by_id(self, package_id: str, customer_id=None) -> TourPackageDetailResponse:
        """Fetch full tour package details by id."""

        package = self.repo.get_by_id(package_id)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )
        return self._format_package_detail(
            package,
            is_wishlist=bool(customer_id and self.repo.is_wishlisted(package.id, customer_id)),
        )

    def get_variant_by_slug(self, package_slug: str, variant_slug: str):
        """Fetch a specific variant for a given package slug."""

        package = self.repo.get_by_slug(package_slug, active_only=True)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PackageError.PACKAGE_NOT_FOUND,
            )

        variant = None
        for item in package.variants:
            if item.slug == variant_slug and item.is_active:
                variant = item
                break

        if variant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant with slug '{variant_slug}' not found for package '{package_slug}'",
            )

        active_variants = [v for v in package.variants if v.is_active]
        other_variants = [self._summarize_variant(v) for v in active_variants if v.id != variant.id]

        return {
            "variant": self._format_variant_detail(variant),
            "other_variants": other_variants,
        }

    @staticmethod
    def _get_default_variant(package: TourPackage | None) -> TourVariant | None:
        if package is None or not package.variants:
            return None
        active_variants = [v for v in package.variants if v.is_active]
        if not active_variants:
            return None
        for variant in active_variants:
            if variant.is_default:
                return variant
        return active_variants[0]

    @staticmethod
    def _extract_banner_media(details) -> dict[str, str | None] | None:
        if not details:
            return None
        banner = getattr(details, "banner", None)
        if isinstance(banner, dict):
            return {
                "image": banner.get("cover_image") or banner.get("url") or banner.get("image") or banner.get("src"),
                "video": banner.get("video") or banner.get("video_url"),
            }
        if isinstance(banner, str):
            return {"image": banner, "video": None}
        return None

    @staticmethod
    def _summarize_variant(variant: TourVariant) -> dict[str, Any]:
        return {
            "slug": variant.slug,
            "name": variant.name,
            "season_name": variant.season_name,
            "badge": variant.badge,
            "availability": variant.availability or "AVAILABLE",
        }

    @classmethod
    def _format_package_detail(
        cls,
        package: TourPackage,
        is_wishlist: bool = False,
    ) -> TourPackageDetailResponse:
        """Transform package and selected/default variants for the frontend."""

        active_variants = [v for v in package.variants if v.is_active]
        default_variant = cls._get_default_variant(package)
        default_payload = cls._format_variant_detail(default_variant) if default_variant else None
        other_variants = [cls._summarize_variant(v) for v in active_variants if default_variant is None or v.id != default_variant.id]

        return TourPackageDetailResponse(
            id=package.id,
            tour_code=package.tour_code,
            slug=package.slug,
            title=package.title,
            destination=package.destination,
            type=package.type,
            description=package.description,
            is_wishlist=is_wishlist,
            default_variant=default_payload,
            other_variants=other_variants,
        )

    @classmethod
    def _format_variant_detail(cls, variant: TourVariant | None) -> Any:
        if variant is None:
            return None

        duration_days = variant.duration_days
        duration_nights = variant.duration_nights
        price_val = float(variant.base_price) if variant.base_price is not None else 0.0

        route: list[Any] = []
        highlights: list[Any] = []
        departure_dates: list[Any] = []
        gallery: list[Any] = []
        itinerary: list[Any] = []
        inclusions: list[Any] = []
        exclusions: list[Any] = []

        details = variant.details
        if details:
            if isinstance(details.banner, dict):
                banner_image = details.banner.get("cover_image") or details.banner.get("url") or details.banner.get("image") or details.banner.get("src")
                banner_video = details.banner.get("video") or details.banner.get("video_url")
                banner_value = {
                    "image": banner_image,
                    "video": banner_video,
                }
            elif isinstance(details.banner, str):
                banner_value = {"image": details.banner, "video": None}
            else:
                banner_value = None

            raw_route = details.route_stops if isinstance(details.route_stops, list) else []
            for i, item in enumerate(raw_route):
                route.append(item if isinstance(item, dict) else {"id": f"r{i+1}", "place": str(item)})

            raw_highlights = details.highlights if isinstance(details.highlights, list) else []
            for i, item in enumerate(raw_highlights):
                highlights.append(item if isinstance(item, dict) else {"id": f"h{i+1}", "text": str(item)})

            raw_dates = details.departures_dates if isinstance(details.departures_dates, list) else []
            for i, item in enumerate(raw_dates):
                departure_dates.append(item if isinstance(item, dict) else {"id": f"d{i+1}", "date": str(item)})

            raw_gallery = details.gallery if isinstance(details.gallery, list) else []
            for i, item in enumerate(raw_gallery):
                gallery.append(item if isinstance(item, dict) else {"id": f"g{i+1}", "photoId": str(item)})

            raw_itinerary = details.itinerary if isinstance(details.itinerary, list) else []
            for i, item in enumerate(raw_itinerary):
                if isinstance(item, dict):
                    itinerary.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    itinerary.append({"id": f"i{i+1}", "day": str(item[0]), "description": str(item[1])})
                elif isinstance(item, str):
                    itinerary.append({"id": f"i{i+1}", "day": f"Day {i+1}", "description": item})

            inclusions = details.inclusions if isinstance(details.inclusions, list) else []
            exclusions = details.exclusions if isinstance(details.exclusions, list) else []
        else:
            banner_value = None

        return {
            "id": variant.id,
            "slug": variant.slug,
            "name": variant.name,
            "badge": variant.badge,
            "season_name": variant.season_name,
            "banner": banner_value,
            "valid_from": variant.valid_from,
            "valid_to": variant.valid_to,
            "duration_days": duration_days,
            "duration_nights": duration_nights,
            "price": price_val,
            "seats": variant.seats,
            "availability": variant.availability or "AVAILABLE",
            "route": route,
            "highlights": highlights,
            "departure_dates": departure_dates,
            "gallery": gallery,
            "itinerary": itinerary,
            "inclusions": inclusions,
            "exclusions": exclusions,
        }

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
            if isinstance(details.banner, dict):
                cover_image = details.banner.get("cover_image") or details.banner.get("url") or details.banner.get("image")
            elif isinstance(details.banner, str):
                cover_image = details.banner

            raw_route = details.route_stops if isinstance(details.route_stops, list) else []
            for i, r in enumerate(raw_route):
                if isinstance(r, dict):
                    route.append(r)
                else:
                    route.append({"id": f"r{i+1}", "place": str(r)})

            raw_hl = details.highlights if isinstance(details.highlights, list) else []
            for i, h in enumerate(raw_hl):
                if isinstance(h, dict):
                    highlights.append(h)
                else:
                    highlights.append({"id": f"h{i+1}", "text": str(h)})

            raw_dates = details.departures_dates if isinstance(details.departures_dates, list) else []
            for i, d in enumerate(raw_dates):
                if isinstance(d, dict):
                    dates.append(d)
                else:
                    dates.append({"id": f"d{i+1}", "date": str(d)})

            raw_gal = details.gallery if isinstance(details.gallery, list) else []
            for i, g in enumerate(raw_gal):
                if isinstance(g, dict):
                    gallery.append(g)
                else:
                    gallery.append({"id": f"g{i+1}", "photoId": str(g)})

            raw_it = details.itinerary if isinstance(details.itinerary, list) else []
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
