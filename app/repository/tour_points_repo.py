import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import (
    AccountRole,
    FinancialAccountOwnerType,
    FinancialAccountType,
    FinancialTransactionCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    PointTransactionType,
    TourType,
)
from app.models.account import Account
from app.models.booking import Booking
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.models.tour_package import TourPackage
from app.models.tour_point_configuration import TourPointConfiguration
from app.models.tour_point_configuration_history import TourPointConfigurationHistory
from app.models.tour_point_transaction import TourPointTransaction


class TourPointsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_configuration(self, tour_type: TourType, *, for_update: bool = False) -> TourPointConfiguration | None:
        stmt = select(TourPointConfiguration).where(TourPointConfiguration.tour_type == tour_type)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_configurations(self) -> list[TourPointConfiguration]:
        return list(
            self.db.execute(select(TourPointConfiguration).order_by(TourPointConfiguration.tour_type)).scalars().all()
        )

    def list_configuration_history(self, tour_type: TourType | None = None) -> list[TourPointConfigurationHistory]:
        stmt = select(TourPointConfigurationHistory).options(
            joinedload(TourPointConfigurationHistory.changed_by_account)
        )
        if tour_type is not None:
            stmt = stmt.where(TourPointConfigurationHistory.tour_type == tour_type)
        return list(self.db.execute(
            stmt.order_by(TourPointConfigurationHistory.changed_at.desc()).limit(200)
        ).scalars().all())

    def list_transactions(
        self,
        *,
        page: int,
        page_size: int,
        account_id: uuid.UUID | None = None,
        booking_id: uuid.UUID | None = None,
        package_id: uuid.UUID | None = None,
        transaction_type: PointTransactionType | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        points_min: Decimal | None = None,
        points_max: Decimal | None = None,
        search: str | None = None,
    ) -> tuple[list[TourPointTransaction], int]:
        stmt = select(TourPointTransaction).join(
            Account, TourPointTransaction.account_id == Account.id
        ).outerjoin(
            Booking, TourPointTransaction.booking_id == Booking.id
        ).outerjoin(
            TourPackage, TourPointTransaction.package_id == TourPackage.id
        ).options(
            joinedload(TourPointTransaction.account),
            joinedload(TourPointTransaction.booking),
            joinedload(TourPointTransaction.package),
        )
        if account_id is not None:
            stmt = stmt.where(TourPointTransaction.account_id == account_id)
        if booking_id is not None:
            stmt = stmt.where(TourPointTransaction.booking_id == booking_id)
        if package_id is not None:
            stmt = stmt.where(TourPointTransaction.package_id == package_id)
        if transaction_type is not None:
            stmt = stmt.where(TourPointTransaction.transaction_type == transaction_type)
        if created_from is not None:
            stmt = stmt.where(TourPointTransaction.created_at >= created_from)
        if created_to is not None:
            stmt = stmt.where(TourPointTransaction.created_at <= created_to)
        if points_min is not None:
            stmt = stmt.where(TourPointTransaction.points >= points_min)
        if points_max is not None:
            stmt = stmt.where(TourPointTransaction.points <= points_max)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(or_(
                Account.name.ilike(term),
                Account.email.ilike(term),
                Account.account_code.ilike(term),
                Booking.booking_code.ilike(term),
                TourPackage.title.ilike(term),
                TourPointTransaction.booking_code.ilike(term),
                TourPointTransaction.tour_title.ilike(term),
            ))

        total = self.db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
        items = self.db.execute(
            stmt.order_by(TourPointTransaction.created_at.desc(), TourPointTransaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().scalars().all()
        return list(items), total

    def ranked_accounts(self, *, page: int, page_size: int, include_spend: bool = False):
        ranked_query = self._ranked_accounts_query()
        if include_spend:
            ranked_query = ranked_query.add_columns(self._customer_spend_expression().label("money_spends"))
        ranked = ranked_query.subquery()
        rows = self.db.execute(
            select(ranked).order_by(ranked.c.rank).offset((page - 1) * page_size).limit(page_size)
        ).all()
        total = self.db.execute(
            select(func.count()).select_from(Account).where(
                Account.role == AccountRole.CUSTOMER,
                Account.is_active.is_(True),
            )
        ).scalar_one()
        return rows, total

    def rank_for_account(self, account_id: uuid.UUID):
        ranked = self._ranked_accounts_query().subquery()
        return self.db.execute(select(ranked).where(ranked.c.account_id == account_id)).one_or_none()

    def nearby_ranked_accounts(self, rank: int, *, radius: int = 2):
        ranked = self._ranked_accounts_query().subquery()
        return self.db.execute(
            select(ranked)
            .where(ranked.c.rank.between(max(1, rank - radius), rank + radius))
            .order_by(ranked.c.rank)
        ).all()

    @staticmethod
    def _ranked_accounts_query():
        return select(
            Account.id.label("account_id"),
            Account.name.label("name"),
            Account.profile_pic.label("profile_pic"),
            Account.created_at.label("customer_joined_at"),
            Account.account_code.label("account_code"),
            Account.points_balance.label("points"),
            func.row_number().over(
                order_by=(Account.points_balance.desc(), Account.id.asc())
            ).label("rank"),
        ).where(
            Account.role == AccountRole.CUSTOMER,
            Account.is_active.is_(True),
        )

    @staticmethod
    def _customer_spend_expression():
        booking_payments = (
            select(
                FinancialTransaction.booking_id.label("booking_id"),
                func.sum(
                    case(
                        (
                            FinancialTransaction.transaction_type == FinancialTransactionType.INCOME,
                            FinancialTransaction.amount,
                        ),
                        (
                            FinancialTransaction.transaction_type == FinancialTransactionType.EXPENSE,
                            -FinancialTransaction.amount,
                        ),
                        else_=0,
                    )
                ).label("net_paid"),
                func.count().label("transaction_count"),
            )
            .where(
                FinancialTransaction.booking_id.is_not(None),
                FinancialTransaction.category == FinancialTransactionCategory.BOOKING_PAYMENT,
                FinancialTransaction.currency == "INR",
                FinancialTransaction.status.in_(
                    (FinancialTransactionStatus.COMPLETED, FinancialTransactionStatus.REVERSED)
                ),
            )
            .group_by(FinancialTransaction.booking_id)
            .subquery()
        )
        booking_spend = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (booking_payments.c.transaction_count > 0, booking_payments.c.net_paid),
                            else_=Booking.paid_amount,
                        )
                    ),
                    0,
                )
            )
            .select_from(Booking)
            .outerjoin(booking_payments, booking_payments.c.booking_id == Booking.id)
            .where(Booking.customer_id == Account.id)
            .scalar_subquery()
        )
        wallet_spend = (
            select(func.coalesce(func.sum(FinancialTransactionEntry.debit - FinancialTransactionEntry.credit), 0))
            .select_from(FinancialTransactionEntry)
            .join(FinancialTransaction, FinancialTransaction.id == FinancialTransactionEntry.transaction_id)
            .join(FinancialAccount, FinancialAccount.id == FinancialTransactionEntry.account_id)
            .where(
                FinancialAccount.owner_id == Account.id,
                FinancialAccount.owner_type == FinancialAccountOwnerType.CUSTOMER,
                FinancialAccount.account_type == FinancialAccountType.LIABILITY,
                FinancialTransaction.category.in_(
                    (FinancialTransactionCategory.WALLET_DEBIT, FinancialTransactionCategory.BOOKING_REFUND)
                ),
                FinancialTransaction.currency == "INR",
                FinancialTransaction.status.in_(
                    (FinancialTransactionStatus.COMPLETED, FinancialTransactionStatus.REVERSED)
                ),
            )
            .scalar_subquery()
        )
        total_spend = booking_spend + wallet_spend
        return case((total_spend < 0, 0), else_=total_spend)
