import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.booking_payment import BookingPayment
from app.repository.booking_repo import BookingRepository
from app.repository.payment_repo import PaymentRepository
from app.schemas.payment import BookingPaymentCreate


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.booking_repo = BookingRepository(db)

    def record_payment(self, payload: BookingPaymentCreate, recorded_by: Account) -> BookingPayment:
        booking = self.booking_repo.get_by_id(payload.booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        payment_data = payload.model_dump()
        payment_data["recorded_by_account_id"] = recorded_by.id

        payment = self.payment_repo.create(payment_data)

        # Update booking paid and due amounts
        if payment.status == "SUCCESS":
            self.booking_repo.update_financials(booking, payment.amount)

        return payment

    def list_booking_payments(self, booking_id: uuid.UUID) -> list[BookingPayment]:
        return self.payment_repo.list_for_booking(booking_id)
