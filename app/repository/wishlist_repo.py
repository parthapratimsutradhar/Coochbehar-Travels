import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import TourType
from app.models.destination import Destination
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.tour_wishlist import TourWishlist


class WishlistRepository:
    """Database operations for customer tour wishlists."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_customer(
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
    ) -> tuple[list[tuple[TourWishlist, TourPackage]], int]:
        filters = [
            TourWishlist.customer_id == customer_id,
            TourPackage.is_active.is_(True),
            TourPackage.variants.any(TourVariant.is_active.is_(True)),
        ]
        if destination:
            filters.append(TourPackage.destination.has(Destination.name.ilike(f"%{destination}%")))
        if tour_type:
            filters.append(TourPackage.type == tour_type)
        if season:
            filters.append(
                TourPackage.variants.any(
                    TourVariant.is_active.is_(True)
                    & TourVariant.season_name.ilike(f"%{season}%")
                )
            )
        if is_featured is not None:
            filters.append(TourPackage.is_featured.is_(is_featured))
        if search:
            term = f"%{search}%"
            filters.append(
                or_(
                    TourPackage.title.ilike(term),
                    TourPackage.destination.has(Destination.name.ilike(term)),
                )
            )

        base_query = select(TourWishlist).join(
            TourPackage,
            TourPackage.id == TourWishlist.package_id,
        ).where(*filters)
        total = self.db.scalar(
            select(func.count()).select_from(base_query.order_by(None).subquery())
        ) or 0
        order_by = (
            TourWishlist.created_at.asc()
            if sort_order == "asc"
            else TourWishlist.created_at.desc()
        )
        rows = self.db.execute(
            base_query.options(
                joinedload(TourWishlist.package)
                .joinedload(TourPackage.variants)
                .joinedload(TourVariant.details),
                joinedload(TourWishlist.package).joinedload(TourPackage.destination),
            )
            .order_by(order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().scalars().all()
        return [(wishlist, wishlist.package) for wishlist in rows], total

    def get_active_package_by_slug(self, package_slug: str) -> TourPackage | None:
        return self.db.scalar(
            select(TourPackage).where(
                TourPackage.slug == package_slug,
                TourPackage.is_active.is_(True),
            )
        )

    def get_customer_entry(self, customer_id: uuid.UUID, package_id: uuid.UUID) -> TourWishlist | None:
        return self.db.scalar(
            select(TourWishlist).where(
                TourWishlist.customer_id == customer_id,
                TourWishlist.package_id == package_id,
            )
        )

    def get_customer_entry_by_slug(
        self,
        customer_id: uuid.UUID,
        package_slug: str,
    ) -> TourWishlist | None:
        return self.db.scalar(
            select(TourWishlist)
            .join(TourPackage, TourPackage.id == TourWishlist.package_id)
            .where(
                TourWishlist.customer_id == customer_id,
                TourPackage.slug == package_slug,
            )
        )

    def add(self, customer_id: uuid.UUID, package_id: uuid.UUID) -> TourWishlist:
        wishlist = TourWishlist(customer_id=customer_id, package_id=package_id)
        self.db.add(wishlist)
        self.db.commit()
        self.db.refresh(wishlist)
        return wishlist

    def delete(self, wishlist: TourWishlist) -> None:
        self.db.delete(wishlist)
        self.db.commit()