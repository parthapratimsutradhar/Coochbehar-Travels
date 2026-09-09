from decimal import Decimal
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.booking_payment import BookingPayment


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, payment_id: uuid.UUID) -> BookingPayment | None:
        stmt = select(BookingPayment).where(BookingPayment.id == payment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_booking(self, booking_id: uuid.UUID) -> list[BookingPayment]:
        stmt = (
            select(BookingPayment)
            .where(BookingPayment.booking_id == booking_id)
            .order_by(BookingPayment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, payment_data: dict) -> BookingPayment:
        payment = BookingPayment(**payment_data)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_total_collections(self) -> Decimal:
        stmt = select(func.coalesce(func.sum(BookingPayment.amount), 0)).where(
            BookingPayment.status == "SUCCESS"
        )
        return Decimal(self.db.execute(stmt).scalar_one())
