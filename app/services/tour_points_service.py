from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, PointTransactionType, TourType
from app.models.account import Account
from app.models.booking import Booking
from app.models.tour_package import TourPackage
from app.models.tour_point_configuration import TourPointConfiguration
from app.models.tour_point_configuration_history import TourPointConfigurationHistory
from app.models.tour_point_transaction import TourPointTransaction
from app.repository.tour_points_repo import TourPointsRepository


POINT_QUANTUM = Decimal("0.0001")
DEFAULT_AMOUNT_PER_POINT = Decimal("10000.00")
DEFAULT_RANKING_PAGE_SIZE = 10
POINT_EARNING_STATUSES = {
    BookingStatus.CONFIRMED,
    BookingStatus.PARTIALLY_PAID,
    BookingStatus.FULLY_PAID,
    BookingStatus.TRAVELLED,
    BookingStatus.COMPLETED,
}
POINT_REVERSAL_STATUSES = {BookingStatus.CANCELLED, BookingStatus.REFUNDED}


class TourPointsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TourPointsRepository(db)

    def get_configurations(self) -> list[TourPointConfiguration]:
        self._ensure_configurations()
        self.db.commit()
        return self.repo.list_configurations()

    def get_configuration_history(self, tour_type: TourType | None = None):
        return self.repo.list_configuration_history(tour_type)

    def update_configuration(
        self,
        tour_type: TourType,
        amount_per_point: Decimal,
        changed_by_account_id: uuid.UUID,
    ) -> TourPointConfiguration:
        if amount_per_point <= 0:
            raise HTTPException(status_code=422, detail="Amount per point must be greater than zero.")
        config = self.repo.get_configuration(tour_type, for_update=True)
        if config is None:
            config = TourPointConfiguration(tour_type=tour_type, amount_per_point=amount_per_point)
            self.db.add(config)
            self.db.flush()
            previous_amount = None
        else:
            previous_amount = config.amount_per_point
            config.amount_per_point = amount_per_point
        config.updated_by_account_id = changed_by_account_id
        self.db.add(TourPointConfigurationHistory(
            configuration_id=config.id,
            tour_type=tour_type,
            previous_amount_per_point=previous_amount,
            amount_per_point=amount_per_point,
            changed_by_account_id=changed_by_account_id,
        ))
        self.db.commit()
        self.db.refresh(config)
        return config

    def award_booking_points(self, booking: Booking) -> TourPointTransaction | None:
        self.db.flush()
        booking = self._lock_booking(booking)
        if booking.status not in POINT_EARNING_STATUSES or booking.points_processed:
            return None

        booking.points_processed = True
        amount = Decimal(booking.total_amount or 0)
        if amount <= 0:
            return None

        config = self.repo.get_configuration(booking.booking_type, for_update=True)
        if config is None:
            self._ensure_configurations()
            config = self.repo.get_configuration(booking.booking_type, for_update=True)
        if config is None or config.amount_per_point <= 0:
            return None

        earned = (amount / config.amount_per_point).quantize(POINT_QUANTUM, rounding=ROUND_HALF_UP)
        booking.points_awarded = earned
        booking.points_amount_per_point = config.amount_per_point
        booking.points_configuration_id = config.id
        if earned <= 0:
            return None

        customer = self.db.execute(
            select(Account)
            .where(Account.id == booking.customer_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
        balance_before = Decimal(customer.points_balance or 0)
        balance_after = balance_before + earned
        customer.points_balance = balance_after
        package = self.db.get(TourPackage, booking.package_id) if booking.package_id else None
        transaction = TourPointTransaction(
            account_id=customer.id,
            booking_id=booking.id,
            package_id=booking.package_id,
            configuration_id=config.id,
            transaction_type=PointTransactionType.BOOKING_EARNED,
            points=earned,
            balance_before=balance_before,
            balance_after=balance_after,
            amount_per_point=config.amount_per_point,
            booking_code=booking.booking_code,
            tour_title=package.title if package else None,
            reason=f"Points earned for booking {booking.booking_code}",
        )
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def reverse_booking_points(self, booking: Booking) -> TourPointTransaction | None:
        self.db.flush()
        booking = self._lock_booking(booking)
        if booking.status not in POINT_REVERSAL_STATUSES or booking.points_reversed_at is not None:
            return None
        earned = Decimal(booking.points_awarded or 0)
        if earned <= 0:
            return None

        customer = self.db.execute(
            select(Account)
            .where(Account.id == booking.customer_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
        balance_before = Decimal(customer.points_balance or 0)
        balance_after = balance_before - earned
        customer.points_balance = balance_after
        booking.points_reversed_at = datetime.now(timezone.utc)
        package = self.db.get(TourPackage, booking.package_id) if booking.package_id else None
        transaction = TourPointTransaction(
            account_id=customer.id,
            booking_id=booking.id,
            package_id=booking.package_id,
            configuration_id=booking.points_configuration_id,
            transaction_type=PointTransactionType.BOOKING_REVERSED,
            points=-earned,
            balance_before=balance_before,
            balance_after=balance_after,
            amount_per_point=booking.points_amount_per_point,
            booking_code=booking.booking_code,
            tour_title=package.title if package else None,
            reason=f"Points reversed for {booking.status.value.lower()} booking {booking.booking_code}",
        )
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def list_transactions(self, **filters):
        return self.repo.list_transactions(**filters)

    def list_rankings(self, *, page: int, page_size: int, include_spend: bool = False):
        return self.repo.ranked_accounts(page=page, page_size=page_size, include_spend=include_spend)

    def get_customer_ranking(self, customer_id: uuid.UUID) -> dict:
        current = self.repo.rank_for_account(customer_id)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer ranking not found.")
        peers = self.repo.nearby_ranked_accounts(current.rank)
        return {"current": current, "peers": peers}

    def get_customer_rank_position(
        self,
        customer_id: uuid.UUID,
        page_size: int = DEFAULT_RANKING_PAGE_SIZE,
    ) -> dict:
        current = self.repo.rank_for_account(customer_id)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer ranking not found.")
        return {
            "rank": current.rank,
            "page_number": ((current.rank - 1) // page_size) + 1,
            "page_size": page_size,
            "point_balance": current.points,
        }

    def _ensure_configurations(self) -> None:
        for tour_type in (TourType.DOMESTIC, TourType.INTERNATIONAL):
            if self.repo.get_configuration(tour_type) is None:
                config = TourPointConfiguration(
                    tour_type=tour_type,
                    amount_per_point=DEFAULT_AMOUNT_PER_POINT,
                )
                self.db.add(config)
                self.db.flush()
                self.db.add(TourPointConfigurationHistory(
                    configuration_id=config.id,
                    tour_type=tour_type,
                    previous_amount_per_point=None,
                    amount_per_point=DEFAULT_AMOUNT_PER_POINT,
                ))

    def _lock_booking(self, booking: Booking) -> Booking:
        return self.db.execute(
            select(Booking)
            .where(Booking.id == booking.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
