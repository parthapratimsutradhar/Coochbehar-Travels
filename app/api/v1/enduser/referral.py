from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.models.customer import Customer
from app.models.referral import Referral
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.referral import (
	ReferralCodeResponse,
	ReferralHistoryItemResponse,
	ReferralInviteResponse,
)
from app.schemas.response import ErrorResponse, SuccessResponse

router = APIRouter(
	prefix="/referrals",
	tags=["Referrals"],
)


@router.get(
	"/invite/{referral_code}",
	response_model=SuccessResponse[ReferralInviteResponse],
	responses={404: {"model": ErrorResponse}},
	summary="Validate a referral invite link",
	description="Resolve a referral link before the friend starts OTP or Google signup.",
)
def validate_referral_invite(
	referral_code: str,
	db: Session = Depends(get_db),
) -> SuccessResponse[ReferralInviteResponse]:
	normalized_code = referral_code.strip().upper()
	referrer = db.query(Customer).filter(
		Customer.referral_code == normalized_code,
	).first()
	if referrer is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Invalid referral code.",
		)
	return SuccessResponse(
		message="Referral invite is valid",
		data=ReferralInviteResponse(
			referral_code=referrer.referral_code,
			referrer_name=referrer.name,
		),
	)


@router.get(
	"/code",
	response_model=SuccessResponse[ReferralCodeResponse],
	responses={401: {"model": ErrorResponse}},
	summary="Get the authenticated customer's referral code",
)
def get_referral_code(
	current_customer: Customer = Depends(get_current_customer),
) -> SuccessResponse[ReferralCodeResponse]:
	return SuccessResponse(
		message="Referral code fetched successfully",
		data=ReferralCodeResponse(
			referral_code=current_customer.referral_code,
		),
	)


@router.get(
	"",
	response_model=PaginatedResponse[ReferralHistoryItemResponse],
	responses={401: {"model": ErrorResponse}},
	summary="List the authenticated customer's referral history",
)
def list_referral_history(
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	current_customer: Customer = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[ReferralHistoryItemResponse]:
	query = (
		db.query(Referral)
		.options(joinedload(Referral.referred_customer), joinedload(Referral.referrer))
		.filter(Referral.referrer_customer_id == current_customer.id)
		.order_by(Referral.created_at.desc())
	)
	total_items = query.count()
	referrals = query.offset((page - 1) * page_size).limit(page_size).all()
	total_pages = (total_items + page_size - 1) // page_size if total_items else 0
	return PaginatedResponse(
		message="Referral history fetched successfully",
		data=[
			ReferralHistoryItemResponse(
				id=item.id,
				referral_code=item.referrer.referral_code,
				status=item.status,
				reward_amount=item.reward_amount,
				reward_issued_at=item.reward_issued_at,
				converted_at=item.converted_at,
				created_at=item.created_at,
				referred_customer=item.referred_customer,
			)
			for item in referrals
		],
		pagination=PaginationMeta(
			current_page=page,
			page_size=page_size,
			total_items=total_items,
			total_pages=total_pages,
			has_next=page < total_pages,
			has_previous=page > 1,
		),
	)
