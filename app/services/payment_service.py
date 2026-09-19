import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.audit_log import AuditLog
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

        external_reference = f"booking-payment:{payload.transaction_id}" if payload.transaction_id else None
        if external_reference:
            existing = self.db.query(FinancialTransaction).filter(
                FinancialTransaction.external_reference == external_reference,
            ).one_or_none()
            if existing is not None:
                return existing
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
            external_reference=external_reference,
            description=payload.notes,
            recorded_by_account_id=recorded_by.id,
            transaction_date=payload.paid_at,
        )

        # Update booking paid and due amounts
        if payment.status == "POSTED":
            self.booking_repo.update_financials(booking, payment.amount)

        self.db.add(AuditLog(
            account_id=recorded_by.id,
            action="BOOKING_PAYMENT_CREATED",
            entity_type="FinancialTransaction",
            entity_id=payment.id,
            new_values={"amount": str(payment.amount), "booking_id": str(booking.id), "payment_method": str(payload.payment_method)},
        ))
        self.db.commit()

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
