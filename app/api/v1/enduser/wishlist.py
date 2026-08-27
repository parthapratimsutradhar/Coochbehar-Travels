from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_customer
from app.core.enums import TourType
from app.core.messages.error import PackageError
from app.db.database import get_db
from app.models.customer import Customer
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.tour_wishlist import TourWishlist
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.tour_package import TourPackageListItem
from app.schemas.wishlist import WishlistItemResponse
from app.services.tour_package_service import TourPackageService

router = APIRouter(
	prefix="/wishlist",
	tags=["Wishlist"],
)


@router.get(
	"",
	response_model=PaginatedResponse[WishlistItemResponse],
	responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="List the authenticated customer's wishlist",
)
def list_wishlist(
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	destination: str | None = Query(None),
	type: TourType | None = Query(None),
	season: str | None = Query(None),
	is_featured: bool | None = Query(None),
	search: str | None = Query(None),
	sort_order: str = Query("desc", pattern="^(asc|desc)$"),
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[WishlistItemResponse]:
	"""Return the customer's active wishlisted packages with filters."""
	query = (
		db.query(TourWishlist, TourPackage)
		.join(TourPackage, TourPackage.id == TourWishlist.package_id)
		.options(joinedload(TourWishlist.package).joinedload(TourPackage.variants))
		.filter(
			TourWishlist.customer_id == current_customer.id,
			TourPackage.is_active.is_(True),
			TourPackage.variants.any(TourVariant.is_active.is_(True)),
		)
	)
	if destination:
		query = query.filter(TourPackage.destination.ilike(f"%{destination}%"))
	if type:
		query = query.filter(TourPackage.type == type)
	if season:
		query = query.filter(
			TourPackage.variants.any(
				(TourVariant.is_active.is_(True))
				& TourVariant.season_name.ilike(f"%{season}%")
			)
		)
	if is_featured is not None:
		query = query.filter(TourPackage.is_featured == is_featured)
	if search:
		term = f"%{search}%"
		query = query.filter(
			or_(TourPackage.title.ilike(term), TourPackage.destination.ilike(term))
		)

	query = query.order_by(
		TourWishlist.created_at.asc()
		if sort_order == "asc"
		else TourWishlist.created_at.desc()
	)
	total_items = query.count()
	rows = query.offset((page - 1) * page_size).limit(page_size).all()
	package_service = TourPackageService(db)
	items = []
	for wishlist, package in rows:
		default_variant = package_service._get_default_variant(package)
		package_item = TourPackageListItem(
			id=package.id,
			tour_code=package.tour_code,
			slug=package.slug,
			title=package.title,
			destination=package.destination,
			type=package.type,
			description=package.description,
			is_featured=package.is_featured,
			season_name=default_variant.season_name if default_variant else None,
			badge=default_variant.badge if default_variant else None,
			banner=(
				package_service._extract_banner_media(default_variant.details)
				if default_variant and default_variant.details
				else None
			),
		)
		items.append(
			WishlistItemResponse(
				id=wishlist.id,
				package_id=package_item.id,
				**package_item.model_dump(exclude={"id"}),
				wishlisted_at=wishlist.created_at,
			)
		)

	total_pages = ceil(total_items / page_size) if total_items else 0
	return PaginatedResponse(
		message="Wishlist fetched successfully",
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


@router.post(
	"/{package_slug}",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
	summary="Add a tour package to the wishlist",
)
def add_to_wishlist(
	package_slug: str,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	package = db.query(TourPackage).filter(
		TourPackage.slug == package_slug,
		TourPackage.is_active.is_(True),
	).first()
	if package is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)
	if db.query(TourWishlist.id).filter(
		TourWishlist.customer_id == current_customer.id,
		TourWishlist.package_id == package.id,
	).first():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tour is already in your wishlist.")

	db.add(TourWishlist(customer_id=current_customer.id, package_id=package.id))
	db.commit()
	return ActionResponse(message="Tour added to wishlist successfully")


@router.delete(
	"/{package_slug}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Remove a tour package from the wishlist",
)
def remove_from_wishlist(
	package_slug: str,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	wishlist = (
		db.query(TourWishlist)
		.join(TourPackage, TourPackage.id == TourWishlist.package_id)
		.filter(
			TourWishlist.customer_id == current_customer.id,
			TourPackage.slug == package_slug,
		)
		.first()
	)
	if wishlist is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour is not in your wishlist.")
	db.delete(wishlist)
	db.commit()
	return ActionResponse(message="Tour removed from wishlist successfully")
