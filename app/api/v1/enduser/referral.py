from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.messages.success import ReferralSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.referral import (
	ReferralCodeResponse,
	ReferralHistoryItemResponse,
	ReferralInviteResponse,
)
from app.schemas.response import ErrorResponse, SuccessResponse
from app.services.referral_service import ReferralService

router = APIRouter(
	prefix="/referrals",
	tags=["Referrals"],
)


@router.get(
	"/invite/{referral_code}",
	response_model=SuccessResponse[ReferralInviteResponse],
	responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
	summary="Validate a referral invite link",
	description="Resolve a referral link before the friend starts OTP or Google signup.",
)
def validate_referral_invite(
	referral_code: str,
	identifier: str | None = Query(
		None,
		description="Optional phone number or email to check referral eligibility (only new accounts can be referred)",
	),
	db: Session = Depends(get_db),
) -> SuccessResponse[ReferralInviteResponse]:
	return SuccessResponse(
		message=ReferralSuccess.INVITE_VALID,
		data=ReferralService(db).validate_invite(referral_code, identifier=identifier),
	)


@router.get(
	"/code",
	response_model=SuccessResponse[ReferralCodeResponse],
	responses={401: {"model": ErrorResponse}},
	summary="Get the authenticated customer's referral code",
)
def get_referral_code(
	current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[ReferralCodeResponse]:
	return SuccessResponse(
		message=ReferralSuccess.CODE_RETRIEVED,
		data=ReferralService(db).get_customer_referral_code(current_customer.id),
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
	items, total_items = ReferralService(db).list_customer_history(
		current_customer.id,
		page,
		page_size,
	)
	total_pages = (total_items + page_size - 1) // page_size if total_items else 0
	return PaginatedResponse(
		message=ReferralSuccess.HISTORY_RETRIEVED,
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
