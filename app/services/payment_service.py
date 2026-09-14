import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.repository.booking_repo import BookingRepository
from app.schemas.payment import BookingPaymentCreate
from app.models.financial_transaction import FinancialTransaction
from app.services.financial_service import FinancialService


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.booking_repo = BookingRepository(db)

    def record_payment(self, payload: BookingPaymentCreate, recorded_by: Account) -> FinancialTransaction:
        booking = self.booking_repo.get_by_id(payload.booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        self.db.commit()
        payment = FinancialService(self.db).record_booking_payment(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            amount=payload.amount,
            currency=payload.currency,
            payment_method=payload.payment_method,
            payment_status=payload.status,
            gateway=payload.gateway,
            gateway_transaction_id=payload.transaction_id,
            description=payload.notes,
            recorded_by_account_id=recorded_by.id,
            transaction_date=payload.paid_at,
        )

        # Update booking paid and due amounts
        if payment.status == "POSTED":
            self.booking_repo.update_financials(booking, payment.amount)

        return payment

    def list_booking_payments(self, booking_id: uuid.UUID) -> list[FinancialTransaction]:
        return list(
            self.db.query(FinancialTransaction)
            .filter(
                FinancialTransaction.booking_id == booking_id,
                FinancialTransaction.transaction_type == "BOOKING_PAYMENT",
            )
            .order_by(FinancialTransaction.created_at.desc())
            .all()
        )
