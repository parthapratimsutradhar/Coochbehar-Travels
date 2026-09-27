from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.core.enums import FinancialTransactionCategory, FinancialTransactionStatus
from app.core.messages.success import WalletSuccess
from app.db.database import get_db
from app.models.account import Account
from app.schemas.financial_transaction import (
    FinancialTransactionResponse,
    financial_transaction_response,
)
from app.schemas.pagination import PaginatedResponse, PaginationMeta
from app.schemas.response import ErrorResponse, SuccessResponse
from app.schemas.wallet import WalletBalanceResponse
from app.services.financial_transaction_service import FinancialTransactionService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "/balance",
    response_model=SuccessResponse[WalletBalanceResponse],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Get the authenticated customer's wallet balance",
)
def get_wallet_balance(
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> SuccessResponse[WalletBalanceResponse]:
    return SuccessResponse(
        message=WalletSuccess.BALANCE_RETRIEVED,
        data=WalletService(db).get_wallet_balance(current_customer.id),
    )


@router.get(
    "",
    response_model=PaginatedResponse[FinancialTransactionResponse],
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List the authenticated customer's financial transactions",
)
def list_customer_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: FinancialTransactionCategory | None = Query(default=None, description="Filter by transaction category"),
    status: FinancialTransactionStatus | None = Query(default=None, description="Filter by transaction status"),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> PaginatedResponse[FinancialTransactionResponse]:
    result = FinancialTransactionService(db).list_transactions(
        customer_id=current_customer.id,
        category=category,
        status=status,
        page=page,
        page_size=page_size,
        exclude_vendor_transactions=True,
    )
    return PaginatedResponse(
        message=WalletSuccess.TRANSACTIONS_RETRIEVED,
        data=[financial_transaction_response(item) for item in result["items"]],
        pagination=PaginationMeta(
            current_page=result["page"],
            page_size=result["page_size"],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            has_next=result["page"] < result["total_pages"],
            has_previous=result["page"] > 1,
        ),
    )
