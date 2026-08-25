import uuid
from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.error import PackageError, ReviewError
from app.core.enums import CustomerTourStatus, EnquiryStatus
from app.db.database import get_db
from app.models.customer import Customer
from app.models.customer_tour import CustomerTour
from app.models.enquiry import Enquiry
from app.models.review import Review
from app.models.tour_package import TourPackage
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

router = APIRouter(
	prefix="/reviews",
	tags=["Reviews"],
)


def _eligible_enquiry_query(db: Session, customer_id: UUID, package_id: UUID):
	return db.query(Enquiry.id).filter(
		Enquiry.customer_id == customer_id,
		Enquiry.package_id == package_id,
		Enquiry.status != EnquiryStatus.CANCELLED,
		or_(
			Enquiry.status == EnquiryStatus.CONVERTED,
			and_(
				Enquiry.travel_date.is_not(None),
				Enquiry.travel_date < date.today(),
			),
		),
	)


def _has_completed_customer_tour(db: Session, customer_id: UUID, package_id: UUID) -> bool:
	return db.query(CustomerTour.id).filter(
		CustomerTour.customer_id == customer_id,
		CustomerTour.package_id == package_id,
		CustomerTour.status == CustomerTourStatus.COMPLETED,
	).first() is not None


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
	package = db.query(TourPackage).filter(TourPackage.slug == package_slug).first()
	if package is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)
	package_id = package.id

	query = (
		db.query(Review)
		.outerjoin(Review.customer)
		.filter(
			Review.package_id == package_id,
			Review.is_published.is_(True),
			Review.is_active.is_(True),
		)
		.order_by(Review.created_at.desc())
	)
	total_items = query.count()
	reviews = query.offset((page - 1) * page_size).limit(page_size).all()
	data = [
		ReviewItemResponse(
			id=review.id,
			review_code=review.review_code,
			reviewer_by=review.customer.name if review.customer else review.name,
			reviewer_pic=review.customer.profile_pic if review.customer else None,
			name=review.name,
			rating=review.rating,
			review=review.review,
			review_gallery=review.review_gallery or [],
			created_at=review.created_at,
		)
		for review in reviews
	]
	total_pages = ceil(total_items / page_size) if total_items else 0
	return PaginatedResponse(
		message="Package reviews fetched successfully",
		data=data,
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=total_items,
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1,
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
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[ReviewEligibilityResponse]:
	package = db.query(TourPackage).filter(TourPackage.slug == package_slug).first()
	if package is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)
	package_id = package.id

	customer_review = db.query(Review).filter(
		Review.customer_id == current_customer.id,
		Review.package_id == package_id,
		Review.is_active.is_(True),
	).first()
	has_reviewed = customer_review is not None
	is_eligible = (
		_eligible_enquiry_query(db, current_customer.id, package_id).first() is not None
		or _has_completed_customer_tour(db, current_customer.id, package_id)
	)
	return SuccessResponse(
		message="Review eligibility fetched successfully",
		data=ReviewEligibilityResponse(
			package_id=package_id,
			can_review=is_eligible and not has_reviewed,
			has_reviewed=has_reviewed,
			review=ReviewResponse.model_validate(customer_review) if customer_review else None,
		),
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
def create_review(
	payload: ReviewCreate,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	package = db.query(TourPackage).filter(TourPackage.id == payload.package_id).first()
	if package is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)

	has_completed_enquiry = _eligible_enquiry_query(
		db,
		current_customer.id,
		payload.package_id,
	).first() is not None
	if not has_completed_enquiry and not _has_completed_customer_tour(
		db,
		current_customer.id,
		payload.package_id,
	):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=ReviewError.TOUR_NOT_COMPLETED,
		)

	existing_review = (
		db.query(Review.id)
		.filter(
			Review.customer_id == current_customer.id,
			Review.package_id == payload.package_id,
		)
		.first()
	)
	if existing_review is not None:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=ReviewError.ALREADY_REVIEWED,
		)

	review = Review(
		review_code=f"REV-{uuid.uuid4().hex[:8].upper()}",
		package_id=payload.package_id,
		customer_id=current_customer.id,
		name=current_customer.name,
		rating=payload.rating,
		review=payload.review,
		review_gallery=payload.review_gallery,
		is_verified=True,
		is_published=True,
	)
	db.add(review)
	db.commit()

	return ActionResponse(message="Review added successfully")


@router.patch(
	"/{review_id}",
	response_model=SuccessResponse[ReviewResponse],
	responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
	summary="Edit a review",
	description="Allow a customer to edit their own review rating, text, or gallery.",
)
def update_review(
	review_id: UUID,
	payload: ReviewUpdate,
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> SuccessResponse[ReviewResponse]:
	review = db.query(Review).filter(
		Review.id == review_id,
		Review.customer_id == current_customer.id,
		Review.is_active.is_(True),
	).first()
	if review is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Review not found.",
		)

	for field, value in payload.model_dump(exclude_unset=True).items():
		setattr(review, field, value)
	db.commit()
	db.refresh(review)

	return SuccessResponse(
		message="Review updated successfully",
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
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> ActionResponse:
	review = db.query(Review).filter(
		Review.id == review_id,
		Review.customer_id == current_customer.id,
		Review.is_active.is_(True),
	).first()
	if review is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Review not found.",
		)

	review.is_active = False
	review.is_published = False
	db.commit()

	return ActionResponse(message="Review deleted successfully")
