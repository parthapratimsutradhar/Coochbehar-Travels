import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer
from app.db.database import get_db
from app.models.account import Account
from app.models.booking import Booking
from app.schemas.response import ErrorResponse, SuccessResponse
from app.schemas.wallet import (
    WalletPaymentCreate,
    WalletResponse,
    WalletTopUpCreate,
    WalletTransactionResponse,
)
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["Enduser - Wallet"])


def _wallet_response(service: WalletService, customer: Account) -> WalletResponse:
    wallet = service.get_wallet_account(customer.id)
    transactions = service.history(customer.id)
    return WalletResponse(
        account_id=wallet.id,
        customer_id=customer.id,
        balance=service.balance(wallet),
        currency=wallet.currency,
        transactions=[WalletTransactionResponse.model_validate(item) for item in transactions],
    )


@router.get("", response_model=SuccessResponse[WalletResponse], summary="View wallet balance and recent transactions")
def get_wallet(
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return SuccessResponse(message="Wallet fetched successfully", data=_wallet_response(WalletService(db), current_customer))


@router.get(
    "/transactions",
    response_model=SuccessResponse[list[WalletTransactionResponse]],
    summary="List wallet transactions",
)
def list_wallet_transactions(
    limit: int = Query(100, ge=1, le=500),
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    transactions = WalletService(db).history(current_customer.id, limit=limit)
    return SuccessResponse(
        message="Wallet transactions fetched successfully",
        data=[WalletTransactionResponse.model_validate(item) for item in transactions],
    )


@router.post(
    "/top-ups",
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
    summary="Record a verified wallet top-up",
)
def top_up_wallet(
    payload: WalletTopUpCreate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    transaction = WalletService(db).record_top_up(
        customer_id=current_customer.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        payment_status=payload.status,
        gateway=payload.gateway,
        gateway_transaction_id=payload.gateway_transaction_id,
        external_reference=payload.external_reference,
        description=payload.description,
    )
    return SuccessResponse(
        message="Wallet top-up processed successfully",
        data=WalletTransactionResponse.model_validate(transaction),
    )


@router.post(
    "/bookings/{booking_id}/payments",
    response_model=SuccessResponse[WalletTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Pay a booking from the wallet",
)
def pay_booking_from_wallet(
    booking_id: uuid.UUID,
    payload: WalletPaymentCreate,
    current_customer: Account = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).one_or_none()
    if booking is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Booking not found.")
    transaction = WalletService(db).pay_booking(
        customer=current_customer,
        booking=booking,
        amount=payload.amount,
        description=payload.description,
    )
    return SuccessResponse(
        message="Booking paid from wallet successfully",
        data=WalletTransactionResponse.model_validate(transaction),
    )
