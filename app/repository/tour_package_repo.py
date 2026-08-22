"""Repository for tour package data access operations.

All raw SQLAlchemy queries live here. The service layer calls these
methods and handles any business-logic transformations.
"""

import math

from sqlalchemy import func, or_, case
from sqlalchemy.orm import Session, joinedload, contains_eager

from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.review import Review
from app.schemas.tour_package import TourPackageFilterParams


class TourPackageRepository:
    """Encapsulates all database queries for tour packages."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────

    def _apply_filters(self, query, filters: TourPackageFilterParams):
        """Apply WHERE clauses based on the filter params."""

        if filters.destination is not None:
            query = query.filter(
                TourPackage.destination.ilike(f"%{filters.destination}%")
            )

        if filters.type is not None:
            query = query.filter(TourPackage.type == filters.type)

        if filters.season is not None:
            season_term = f"%{filters.season}%"
            query = query.filter(
                TourPackage.id.in_(
                    self.db.query(TourVariant.package_id)
                    .filter(TourVariant.is_active == True)
                    .filter(TourVariant.season_name.ilike(season_term))
                    .distinct()
                )
            )

        if filters.is_featured is not None:
            query = query.filter(TourPackage.is_featured == filters.is_featured)

        if filters.is_active is not None:
            query = query.filter(TourPackage.is_active == filters.is_active)

        if filters.search is not None:
            term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    TourPackage.title.ilike(term),
                    TourPackage.destination.ilike(term),
                )
            )

        return query

    @staticmethod
    def _apply_sorting(query, filters: TourPackageFilterParams):
        """Apply ORDER BY clause based on the filter params."""

        allowed_sort_fields = {
            "created_at": TourPackage.created_at,
            "title": TourPackage.title,
            "destination": TourPackage.destination,
            "updated_at": TourPackage.updated_at,
        }

        sort_col = allowed_sort_fields.get(filters.sort_by, TourPackage.created_at)

        if filters.sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        return query

    # ── public methods ───────────────────────────────────────────────

    def get_paginated_list(
        self,
        page: int,
        page_size: int,
        filters: TourPackageFilterParams,
    ) -> tuple[list[dict], int]:
        """Return a paginated, filtered, and sorted list of tour packages.

        Each item is enriched with denormalized variant info:
        starting_price, duration_days, duration_nights, variant_count.

        Returns:
            tuple of (list of result dicts, total_count int)
        """

        # ── Subquery: aggregate variant stats per package ────────────
        variant_stats = (
            self.db.query(
                TourVariant.package_id,
                func.min(TourVariant.base_price).label("starting_price"),
                func.count(TourVariant.id).label("variant_count"),
            )
            .filter(TourVariant.is_active == True)  # noqa: E712
            .group_by(TourVariant.package_id)
            .subquery("variant_stats")
        )

        # ── Subquery: default variant for duration ───────────────────
        default_variant = (
            self.db.query(
                TourVariant.package_id,
                TourVariant.duration_days,
                TourVariant.duration_nights,
            )
            .filter(
                TourVariant.is_default == True,  # noqa: E712
                TourVariant.is_active == True,  # noqa: E712
            )
            .subquery("default_variant")
        )

        # ── Main query ───────────────────────────────────────────────
        query = (
            self.db.query(
                TourPackage,
                variant_stats.c.starting_price,
                variant_stats.c.variant_count,
                default_variant.c.duration_days,
                default_variant.c.duration_nights,
            )
            .outerjoin(
                variant_stats,
                TourPackage.id == variant_stats.c.package_id,
            )
            .outerjoin(
                default_variant,
                TourPackage.id == default_variant.c.package_id,
            )
        )

        # ── Apply filters ────────────────────────────────────────────
        query = self._apply_filters(query, filters)

        # Price filters operate on the aggregated starting_price
        if filters.min_price is not None:
            query = query.filter(
                variant_stats.c.starting_price >= filters.min_price
            )
        if filters.max_price is not None:
            query = query.filter(
                variant_stats.c.starting_price <= filters.max_price
            )

        # ── Total count (before pagination) ──────────────────────────
        total_count = query.count()

        # ── Sorting ──────────────────────────────────────────────────
        if filters.sort_by == "starting_price":
            col = variant_stats.c.starting_price
            if filters.sort_order.lower() == "asc":
                query = query.order_by(col.asc().nullslast())
            else:
                query = query.order_by(col.desc().nullslast())
        else:
            query = self._apply_sorting(query, filters)

        # ── Pagination ───────────────────────────────────────────────
        offset = (page - 1) * page_size
        rows = query.offset(offset).limit(page_size).all()

        # ── Transform to dicts ───────────────────────────────────────
        results: list[dict] = []
        for row in rows:
            package: TourPackage = row[0]
            results.append(
                {
                    "id": package.id,
                    "tour_code": package.tour_code,
                    "slug": package.slug,
                    "title": package.title,
                    "destination": package.destination,
                    "type": package.type,
                    "description": package.description,
                    "is_featured": package.is_featured,
                    "is_active": package.is_active,
                    "created_at": package.created_at,
                    "updated_at": package.updated_at,
                    "starting_price": float(row[1]) if row[1] is not None else None,
                    "variant_count": row[2] or 0,
                    "duration_days": row[3],
                    "duration_nights": row[4],
                }
            )

        return results, total_count

    def get_active_for_selection(
        self,
        search: str | None = None,
        limit: int = 5,
    ) -> list[TourPackage]:
        """Return active packages with at least one active variant for selectors."""

        query = (
            self.db.query(TourPackage)
            .options(joinedload(TourPackage.variants).joinedload(TourVariant.details))
            .filter(TourPackage.is_active == True)  # noqa: E712
            .filter(TourPackage.variants.any(TourVariant.is_active == True))  # noqa: E712
        )
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    TourPackage.title.ilike(term),
                    TourPackage.destination.ilike(term),
                )
            )
        return query.order_by(TourPackage.title.asc()).limit(limit).all()

    def get_by_slug(self, slug: str, active_only: bool = False) -> TourPackage | None:
        """Fetch a single tour package by slug, eagerly loading variants, details, and reviews."""

        query = (
            self.db.query(TourPackage)
            .options(
                joinedload(TourPackage.variants).joinedload(TourVariant.details),
                joinedload(TourPackage.reviews).joinedload(Review.customer),
            )
            .filter(TourPackage.slug == slug)
        )
        if active_only:
            query = query.filter(TourPackage.is_active == True)  # noqa: E712
        return query.first()

    def get_by_id(self, package_id) -> TourPackage | None:
        """Fetch a single tour package by id, eagerly loading variants, details, and reviews."""

        return (
            self.db.query(TourPackage)
            .options(
                joinedload(TourPackage.variants).joinedload(TourVariant.details),
                joinedload(TourPackage.reviews).joinedload(Review.customer),
            )
            .filter(TourPackage.id == package_id)
            .first()
        )
