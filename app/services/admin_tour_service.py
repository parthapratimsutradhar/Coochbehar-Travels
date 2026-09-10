import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.enums import TourType
from app.models.destination import Destination
from app.models.tour_detail import TourDetail
from app.models.tour_departure import TourDeparture
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.repository.admin_tour_repo import AdminTourRepository
from app.schemas.admin_tour import (
    AdminTourDetailPayload,
    AdminTourPackageItem,
    AdminTourVariantItem,
    normalize_json_payload,
)


class AdminTourService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminTourRepository(db)

    def list_packages(
        self,
        page: int,
        page_size: int,
        is_active: bool | None = None,
        is_featured: bool | None = None,
        type: TourType | None = None,
        search: str | None = None,
    ):
        query = (
            self.db.query(TourPackage)
            .outerjoin(TourPackage.destination)
            .options(selectinload(TourPackage.destination))
        )
        if is_active is not None:
            query = query.filter(TourPackage.is_active.is_(is_active))
        if is_featured is not None:
            query = query.filter(TourPackage.is_featured.is_(is_featured))
        if type is not None:
            query = query.filter(TourPackage.type == type)
        if search:
            term = f"%{search}%"
            query = query.filter(
                (
                    TourPackage.title.ilike(term)
                    | TourPackage.slug.ilike(term)
                    | Destination.name.ilike(term)
                    | TourPackage.tour_code.ilike(term)
                )
            )

        total_items = query.count()
        packages = query.order_by(TourPackage.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0
        return {
            "items": [self._package_to_response(item) for item in packages],
            "total_items": total_items,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
        }

    def get_package(self, package_id: uuid.UUID) -> TourPackage:
        package = self.repo.get_package_by_id(package_id)
        if package is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")
        return package

    def create_package(self, payload: dict[str, Any]) -> TourPackage:
        destination_id = payload.get("destination_id")
        if destination_id is not None:
            destination = self.db.get(Destination, destination_id)
            if destination is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")

        if self.repo.get_package_by_code_or_slug(payload["tour_code"], payload["slug"]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A tour package with this code or slug already exists.")

        package = TourPackage(**payload)
        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        return package

    def update_package(self, package_id: uuid.UUID, payload: dict[str, Any]) -> TourPackage:
        package = self.get_package(package_id)

        if "destination_id" in payload and payload.get("destination_id") is not None:
            destination = self.db.get(Destination, payload["destination_id"])
            if destination is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found.")

        for field, value in payload.items():
            setattr(package, field, value)
        self.db.commit()
        self.db.refresh(package)
        return package

    def delete_package(self, package_id: uuid.UUID) -> TourPackage:
        package = self.get_package(package_id)
        package.is_active = False
        self.db.commit()
        return package

    def list_variants(self, tour_id: uuid.UUID | None = None, page: int = 1, page_size: int = 10, is_active: bool | None = None):
        query = self.db.query(TourVariant)
        if tour_id is not None:
            query = query.filter(TourVariant.package_id == tour_id)
        if is_active is not None:
            query = query.filter(TourVariant.is_active.is_(is_active))

        total_items = query.count()
        variants = query.order_by(TourVariant.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        total_pages = (total_items + page_size - 1) // page_size if total_items else 0
        return {
            "items": [self._variant_to_response(item) for item in variants],
            "total_items": total_items,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
        }

    def get_variant(self, variant_id: uuid.UUID) -> TourVariant:
        variant = self.repo.get_variant_by_id(variant_id)
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour variant not found.")
        return variant

    def create_variant(self, payload: dict[str, Any]) -> TourVariant:
        package = self.db.get(TourPackage, payload["tour_id"])
        if package is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour package not found.")

        if self.repo.get_variant_by_slug(payload["slug"]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A tour variant with this slug already exists.")

        list_price = Decimal(str(payload.get("list_price", payload.get("selling_price", 0))))
        selling_price = Decimal(str(payload.get("selling_price", list_price)))
        variant = TourVariant(
            package_id=package.id,
            slug=payload["slug"],
            name=payload["name"],
            season_name=payload.get("season_name"),
            valid_from=date.fromisoformat(payload["valid_from"]),
            valid_to=date.fromisoformat(payload["valid_to"]),
            duration_days=payload["duration_days"],
            duration_nights=payload["duration_nights"],
            list_price=list_price,
            selling_price=selling_price,
            badge=payload.get("badge"),
            is_default=payload.get("is_default", False),
            is_active=payload.get("is_active", True),
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_variant(self, variant_id: uuid.UUID, payload: dict[str, Any]) -> TourVariant:
        variant = self.get_variant(variant_id)
        update_data = payload.copy()

        if "list_price" in update_data:
            update_data["list_price"] = Decimal(str(update_data["list_price"]))
        if "selling_price" in update_data:
            update_data["selling_price"] = Decimal(str(update_data["selling_price"]))
        if "valid_from" in update_data and isinstance(update_data["valid_from"], str):
            update_data["valid_from"] = date.fromisoformat(update_data["valid_from"])
        if "valid_to" in update_data and isinstance(update_data["valid_to"], str):
            update_data["valid_to"] = date.fromisoformat(update_data["valid_to"])

        for field, value in update_data.items():
            if hasattr(variant, field):
                setattr(variant, field, value)

        self.db.commit()
        self.db.refresh(variant)
        return variant

    def delete_variant(self, variant_id: uuid.UUID) -> TourVariant:
        variant = self.get_variant(variant_id)
        variant.is_active = False
        self.db.commit()
        return variant

    def get_detail_by_id(self, detail_id: uuid.UUID) -> TourDetail:
        detail = self.repo.get_detail_by_id(detail_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour detail not found.")
        return detail

    def get_variant_departures(self, variant_id: uuid.UUID) -> list[TourDeparture]:
        return (
            self.db.query(TourDeparture)
            .filter(TourDeparture.variant_id == variant_id)
            .order_by(TourDeparture.departure_date.asc(), TourDeparture.created_at.asc())
            .all()
        )

    def create_detail(self, payload: dict[str, Any]) -> TourDetail:
        variant = self.db.get(TourVariant, payload["variant_id"])
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour variant not found.")

        if self.repo.get_detail_by_variant_id(payload["variant_id"]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This variant already has details.")

        detail = TourDetail(
            variant_id=payload["variant_id"],
            banner=normalize_json_payload(payload.get("banner")) or {"image": None, "video": None},
            gallery=normalize_json_payload(payload.get("gallery")) or [],
            highlights=normalize_json_payload(payload.get("highlights")) or [],
            inclusions=normalize_json_payload(payload.get("inclusions")) or [],
            exclusions=normalize_json_payload(payload.get("exclusions")) or [],
            itinerary=normalize_json_payload(payload.get("itinerary")) or [],
            route_stops=normalize_json_payload(payload.get("route")) or [],
        )
        self.db.add(detail)
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def update_detail(self, detail_id: uuid.UUID, payload: dict[str, Any]) -> TourDetail:
        detail = self.get_detail_by_id(detail_id)
        for key, value in payload.items():
            if key == "banner":
                detail.banner = normalize_json_payload(value) or {"image": None, "video": None}
            elif key == "gallery":
                detail.gallery = normalize_json_payload(value) or []
            elif key == "highlights":
                detail.highlights = normalize_json_payload(value) or []
            elif key == "inclusions":
                detail.inclusions = normalize_json_payload(value) or []
            elif key == "exclusions":
                detail.exclusions = normalize_json_payload(value) or []
            elif key == "departure_dates":
                if hasattr(detail, "departures_dates"):
                    detail.departures_dates = normalize_json_payload(value) or []
            elif key == "itinerary":
                detail.itinerary = normalize_json_payload(value) or []
            elif key == "route":
                detail.route_stops = normalize_json_payload(value) or []
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def delete_detail(self, detail_id: uuid.UUID) -> TourDetail:
        detail = self.get_detail_by_id(detail_id)
        self.db.delete(detail)
        self.db.commit()
        return detail

    def get_package_variant_details(self, package_id: uuid.UUID, variant_id: uuid.UUID) -> TourDetail:
        package = self.get_package(package_id)
        variant = self.get_variant(variant_id)
        if variant.package_id != package.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour variant not found for this package.")
        if variant.details is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour variant details not found.")
        return variant.details

    @staticmethod
    def _package_to_response(item: TourPackage) -> AdminTourPackageItem:
        destination_name = item.destination.name if item.destination else None
        return AdminTourPackageItem(
            id=item.id,
            tour_code=item.tour_code,
            slug=item.slug,
            title=item.title,
            destination=destination_name,
            type=item.type,
            description=item.description,
            is_featured=item.is_featured,
            is_active=item.is_active,
        )

    @staticmethod
    def _variant_to_response(item: TourVariant) -> AdminTourVariantItem:
        return AdminTourVariantItem(
            id=item.id,
            tour_id=item.package_id,
            slug=item.slug,
            name=item.name,
            season_name=item.season_name,
            valid_from=str(item.valid_from),
            valid_to=str(item.valid_to),
            duration_days=item.duration_days,
            duration_nights=item.duration_nights,
            list_price=float(item.list_price),
            selling_price=float(item.selling_price),
            badge=item.badge,
            is_default=item.is_default,
            is_active=item.is_active,
        )

    @staticmethod
    def _detail_to_response(
        detail: TourDetail,
        package_id: uuid.UUID | None = None,
        departures: list[TourDeparture] | None = None,
    ) -> AdminTourDetailPayload:
        raw_highlights = detail.highlights if isinstance(detail.highlights, list) else []
        highlights = []
        for index, item in enumerate(raw_highlights):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("id", f"h{index + 1}")
                row.setdefault("text", str(row.get("text") or ""))
                highlights.append(row)
            else:
                highlights.append({"id": f"h{index + 1}", "text": str(item)})

        raw_gallery = detail.gallery if isinstance(detail.gallery, list) else []
        gallery = []
        for index, item in enumerate(raw_gallery):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("id", f"g{index + 1}")
                row.setdefault("alt", row.get("alt") or "")
                row.setdefault("url", row.get("url") or "")
                row.setdefault("type", row.get("type") or "image")
                row.setdefault("display_order", index + 1)
                gallery.append(row)
            else:
                gallery.append({"id": f"g{index + 1}", "alt": "", "url": str(item), "type": "image", "display_order": index + 1})

        raw_itinerary = detail.itinerary if isinstance(detail.itinerary, list) else []
        itinerary = []
        for index, item in enumerate(raw_itinerary):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("id", f"i{index + 1}")
                row.setdefault("day", row.get("day", index + 1))
                row.setdefault("title", row.get("title") or "")
                row.setdefault("description", row.get("description") or "")
                itinerary.append(row)
            else:
                itinerary.append({"id": f"i{index + 1}", "day": index + 1, "title": str(item), "description": ""})

        raw_route = detail.route_stops if isinstance(detail.route_stops, list) else []
        route = []
        for index, item in enumerate(raw_route):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("id", f"r{index + 1}")
                row.setdefault("city", row.get("city") or "")
                row.setdefault("nights", row.get("nights", 0))
                route.append(row)
            else:
                route.append({"id": f"r{index + 1}", "city": str(item), "nights": 0})

        normalized_departures = departures or []
        departure_dates = [
            {
                "id": str(item.id),
                "departure_date": item.departure_date.isoformat() if item.departure_date else None,
                "return_date": item.return_date.isoformat() if item.return_date else None,
                "total_seats": item.total_seats,
                "available_seats": item.available_seats,
            }
            for item in normalized_departures
        ]

        return AdminTourDetailPayload(
            id=detail.id,
            tour_id=package_id,
            variant_id=detail.variant_id,
            banner=detail.banner if isinstance(detail.banner, dict) else {"image": detail.banner} if isinstance(detail.banner, str) else None,
            gallery=gallery,
            highlights=highlights,
            inclusions=detail.inclusions if isinstance(detail.inclusions, list) else [],
            exclusions=detail.exclusions if isinstance(detail.exclusions, list) else [],
            departure_dates=departure_dates,
            itinerary=itinerary,
            route=route,
        )

