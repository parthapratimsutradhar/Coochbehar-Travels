import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.error import PackageError, ReviewError
from app.core.enums import EnquiryStatus
from app.db.database import get_db
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.review import Review
from app.models.tour_package import TourPackage
from app.schemas.response import ErrorResponse, SuccessResponse
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(
	prefix="/reviews",
	tags=["Reviews"],
)


@router.post(
	"",
	response_model=SuccessResponse[ReviewResponse],
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
) -> SuccessResponse[ReviewResponse]:
	package = db.query(TourPackage).filter(TourPackage.id == payload.package_id).first()
	if package is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PackageError.PACKAGE_NOT_FOUND)

	eligible_enquiry = (
		db.query(Enquiry.id)
		.filter(
			Enquiry.customer_id == current_customer.id,
			Enquiry.package_id == payload.package_id,
			Enquiry.status != EnquiryStatus.CANCELLED,
			or_(
				Enquiry.status == EnquiryStatus.CONVERTED,
				and_(
					Enquiry.travel_date.is_not(None),
					Enquiry.travel_date < date.today(),
				),
			),
		)
		.first()
	)
	if eligible_enquiry is None:
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
	db.refresh(review)

	return SuccessResponse(
		message="Review added successfully",
		data=ReviewResponse.model_validate(review),
	)
