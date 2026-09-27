from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import ReviewSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ActionResponse, ErrorResponse
from app.schemas.response import SuccessResponse
from app.schemas.review import (
	ReviewCreate,
	ReviewEligibilityResponse,
	ReviewResponse,
	ReviewUpdate,
)
from app.schemas.tour_package import ReviewItemResponse
from app.services.review_service import ReviewService

router = APIRouter(
	prefix="/reviews",
	tags=["Reviews"],
)


@router.get(
	"/package/{package_slug}",
	response_model=PaginatedResponse[ReviewItemResponse],
	response_model_exclude_unset=True,
	responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="List published reviews for a package",
	description="Return published reviews, including each review's gallery, for a tour package.",
)
def list_package_reviews(
	package_slug: str,
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	db: Session = Depends(get_db),
) -> PaginatedResponse[ReviewItemResponse]:
	result = ReviewService(db).list_published_reviews(package_slug, page, page_size)
	return PaginatedResponse(
		message=ReviewSuccess.RETRIEVED,
		data=result["items"],
		pagination=PaginationMeta(
			current_page=result["page"],
			page_size=result["page_size"],
			total_items=result["total_items"],
			total_pages=result["total_pages"],
			has_next=result["page"] < result["total_pages"],
			has_previous=result["page"] > 1,
		),
	)


@router.get(
	"/eligibility/{package_slug}",
	response_model=SuccessResponse[ReviewEligibilityResponse],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Check whether the customer can review a package",
)
def get_review_eligibility(
	package_slug: str,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[ReviewEligibilityResponse]:
	return SuccessResponse(
		message=ReviewSuccess.ELIGIBILITY_RETRIEVED,
		data=ReviewService(db).get_customer_eligibility(package_slug, current_customer.id),
	)


@router.post(
	"",
	response_model=ActionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={
		401: {"model": ErrorResponse},
		403: {"model": ErrorResponse},
		404: {"model": ErrorResponse},
		409: {"model": ErrorResponse},
		422: {"model": ErrorResponse},
	},
	summary="Add a review for a previous tour",
	description="Authenticated customers can review a tour linked to a converted or past enquiry.",
)
async def create_review(
	payload: ReviewCreate,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	await ReviewService(db).create_customer_review(current_customer, payload)

	return ActionResponse(message=ReviewSuccess.CREATED)


@router.patch(
	"/{review_id}",
	response_model=SuccessResponse[ReviewResponse],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="Edit a review",
	description="Allow a customer to edit their own review rating, text, or gallery.",
)
async def update_review(
	review_id: UUID,
	payload: ReviewUpdate,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[ReviewResponse]:
	review = await ReviewService(db).update_customer_review(review_id, current_customer.id, payload)

	return SuccessResponse(
		message=ReviewSuccess.UPDATED,
		data=ReviewResponse.model_validate(review),
	)


@router.delete(
	"/{review_id}",
	response_model=ActionResponse,
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="Delete a review",
	description="Allow a customer to delete their own review.",
)
def delete_review(
	review_id: UUID,
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	ReviewService(db).delete_customer_review(review_id, current_customer.id)

	return ActionResponse(message=ReviewSuccess.DELETED)
