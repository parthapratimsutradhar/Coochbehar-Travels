from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import TourType
from app.core.messages.success import WishlistSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.wishlist import WishlistItemResponse
from app.services.wishlist_service import WishlistService

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
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[WishlistItemResponse]:
	"""Return the customer's active wishlisted packages with filters."""
	return WishlistService(db).list_wishlist(
		customer_id=current_customer.id,
		page=page,
		page_size=page_size,
		destination=destination,
		tour_type=type,
		season=season,
		is_featured=is_featured,
		search=search,
		sort_order=sort_order,
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
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	WishlistService(db).add_to_wishlist(current_customer.id, package_slug)
	return ActionResponse(message=WishlistSuccess.CREATED)


@router.delete(
	"/{package_slug}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Remove a tour package from the wishlist",
)
def remove_from_wishlist(
	package_slug: str,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	WishlistService(db).remove_from_wishlist(current_customer.id, package_slug)
	return ActionResponse(message=WishlistSuccess.DELETED)
