from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.models.account import Account
from app.models.customer_profile import CustomerProfile
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
	referrer_profile = (
		db.query(CustomerProfile)
		.options(joinedload(CustomerProfile.account))
		.filter(CustomerProfile.referral_code == normalized_code)
		.first()
	)
	if referrer_profile is None or referrer_profile.account is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Invalid referral code.",
		)
	return SuccessResponse(
		message="Referral invite is valid",
		data=ReferralInviteResponse(
			referral_code=referrer_profile.referral_code,
			referrer_name=referrer_profile.account.name,
		),
	)


@router.get(
	"/code",
	response_model=SuccessResponse[ReferralCodeResponse],
	responses={401: {"model": ErrorResponse}},
	summary="Get the authenticated customer's referral code",
)
def get_referral_code(
	current_customer: Account = Depends(get_current_customer),
) -> SuccessResponse[ReferralCodeResponse]:
	referral_code = (
		current_customer.customer_profile.referral_code
		if current_customer.customer_profile is not None
		else ""
	)
	return SuccessResponse(
		message="Referral code fetched successfully",
		data=ReferralCodeResponse(
			referral_code=referral_code,
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
	current_customer: Account = Depends(get_current_customer),
	db: Session = Depends(get_db),
) -> PaginatedResponse[ReferralHistoryItemResponse]:
	query = (
		db.query(Referral)
		.options(
			joinedload(Referral.referred_customer),
			joinedload(Referral.referrer).joinedload(Account.customer_profile),
		)
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
				referral_code=(
					item.referrer.customer_profile.referral_code
					if item.referrer and item.referrer.customer_profile is not None
					else ""
				),
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
