from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.core.enums import (
    BookingStatus,
    FinancialAccountOwnerType,
    FinancialAccountType,
    FinancialTransactionCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    NON_COLLECTABLE_BOOKING_STATUSES,
    TourType,
)
from app.models.account import Account
from app.models.booking import Booking
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.models.trip_items import TripItem
from app.schemas.financial_reports import (
    FinancialDashboardResponse,
    FinancialReportResponse,
    OutstandingBookingResponse,
)


CONFIRMED_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.PARTIALLY_PAID,
    BookingStatus.FULLY_PAID,
    BookingStatus.TRAVELLED,
    BookingStatus.COMPLETED,
)


class FinancialReportingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _sum_transactions(self, transaction_type: FinancialTransactionType | None = None) -> Decimal:
        query = self.db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0)).filter(
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED
        )
        if transaction_type is not None:
            query = query.filter(FinancialTransaction.transaction_type == transaction_type)
        return Decimal(query.scalar() or 0)

    def dashboard(self) -> FinancialDashboardResponse:
        revenue = Decimal(self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
            Booking.status != BookingStatus.CANCELLED
        ).scalar() or 0)
        collections = self.db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0)).filter(
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED,
            FinancialTransaction.category.in_([
                FinancialTransactionCategory.BOOKING_PAYMENT,
                FinancialTransactionCategory.WALLET_CREDIT,
                FinancialTransactionCategory.REFERRAL_REWARD,
            ]),
        ).scalar() or 0
        expenses = self.db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0)).filter(
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED,
            FinancialTransaction.category.in_([
                FinancialTransactionCategory.VENDOR_PAYMENT,
                FinancialTransactionCategory.ADJUSTMENT,
                FinancialTransactionCategory.WALLET_DEBIT,
                FinancialTransactionCategory.BOOKING_REFUND,
            ]),
        ).scalar() or 0
        direct_cost = Decimal(self.db.query(func.coalesce(func.sum(TripItem.total_price), 0)).filter(TripItem.booking_id.is_not(None)).scalar() or 0)
        customer_outstanding = Decimal(self.db.query(func.coalesce(func.sum(Booking.due_amount), 0)).filter(
            Booking.due_amount > 0,
            Booking.status.notin_(NON_COLLECTABLE_BOOKING_STATUSES),
        ).scalar() or 0)
        vendor_payables = Decimal(0)
        future_revenue = Decimal(self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
            Booking.status.in_(CONFIRMED_STATUSES)
        ).scalar() or 0)
        future_cost = Decimal(self.db.query(func.coalesce(func.sum(TripItem.total_price), 0)).join(
            Booking, Booking.id == TripItem.booking_id
        ).filter(Booking.status.in_(CONFIRMED_STATUSES)).scalar() or 0)
        future_collections = Decimal(self.db.query(func.coalesce(func.sum(Booking.paid_amount), 0)).filter(
            Booking.status.in_(CONFIRMED_STATUSES)
        ).scalar() or 0)
        future_outstanding = Decimal(self.db.query(func.coalesce(func.sum(Booking.due_amount), 0)).filter(
            Booking.status.in_(CONFIRMED_STATUSES)
        ).scalar() or 0)
        expected_vendor = Decimal(0)
        wallet_credits = self._wallet_entry_sum("credit")
        wallet_debits = self._wallet_entry_sum("debit")
        return FinancialDashboardResponse(
            total_revenue=revenue,
            total_collections=collections,
            total_expenses=expenses,
            gross_profit=revenue - direct_cost,
            net_profit=revenue - direct_cost - expenses,
            customer_outstanding=customer_outstanding,
            vendor_payables=vendor_payables,
            confirmed_future_revenue=future_revenue,
            projected_future_cost=future_cost,
            projected_future_profit=future_revenue - future_cost,
            future_customer_collections=future_collections,
            future_customer_outstanding=future_outstanding,
            expected_vendor_payments=expected_vendor,
            customer_wallet_balances=wallet_credits - wallet_debits,
            wallet_credits=wallet_credits,
            wallet_debits=wallet_debits,
        )

    def list_outstanding_bookings(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        booking_status: BookingStatus | None = None,
        tour_type: TourType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        departure_start_date: date | None = None,
        departure_end_date: date | None = None,
        min_due: Decimal | None = None,
        max_due: Decimal | None = None,
        search: str | None = None,
    ) -> tuple[list[OutstandingBookingResponse], int]:
        query = self.db.query(Booking, Account).join(
            Account, Account.id == Booking.customer_id
        ).filter(
            Booking.due_amount > 0,
            Booking.status.notin_(NON_COLLECTABLE_BOOKING_STATUSES),
        )
        if customer_id is not None:
            query = query.filter(Booking.customer_id == customer_id)
        if booking_status is not None:
            query = query.filter(Booking.status == booking_status)
        if tour_type is not None:
            query = query.filter(Booking.booking_type == tour_type)
        if start_date is not None:
            query = query.filter(Booking.created_at >= datetime.combine(start_date, time.min))
        if end_date is not None:
            query = query.filter(Booking.created_at < datetime.combine(end_date + timedelta(days=1), time.min))
        if departure_start_date is not None:
            query = query.filter(Booking.departure_date >= departure_start_date)
        if departure_end_date is not None:
            query = query.filter(Booking.departure_date <= departure_end_date)
        if min_due is not None:
            query = query.filter(Booking.due_amount >= min_due)
        if max_due is not None:
            query = query.filter(Booking.due_amount <= max_due)
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Booking.booking_code.ilike(search_term),
                    Account.name.ilike(search_term),
                    Account.email.ilike(search_term),
                    Account.mobile.ilike(search_term),
                )
            )

        total_items = query.count()
        rows = query.order_by(Booking.created_at.desc(), Booking.id).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        items = [
            OutstandingBookingResponse(
                booking_id=booking.id,
                booking_code=booking.booking_code,
                customer_id=customer.id,
                customer_name=customer.name,
                customer_email=customer.email,
                customer_mobile=customer.mobile,
                status=booking.status.value,
                departure_date=booking.departure_date,
                created_at=booking.created_at,
                total_amount=booking.total_amount,
                paid_amount=booking.paid_amount,
                due_amount=booking.due_amount,
            )
            for booking, customer in rows
        ]
        return items, total_items

    def _wallet_entry_sum(self, column: str) -> Decimal:
        value = getattr(FinancialTransactionEntry, column)
        result = self.db.query(func.coalesce(func.sum(value), 0)).join(
            FinancialAccount, FinancialAccount.id == FinancialTransactionEntry.account_id
        ).join(
            FinancialTransaction, FinancialTransaction.id == FinancialTransactionEntry.transaction_id
        ).filter(
            FinancialAccount.owner_type == FinancialAccountOwnerType.CUSTOMER,
            FinancialAccount.account_type == FinancialAccountType.LIABILITY,
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED,
        ).scalar()
        return Decimal(result or 0)

    def report(self, report_type: str, start: date | None = None, end: date | None = None) -> FinancialReportResponse:
        supported = {
            "revenue", "collections", "outstanding", "expenses", "booking-profitability",
            "vendor-payments", "wallet-transactions", "payment-method", "destination-profitability",
            "tour-profitability", "monthly", "yearly",
        }
        normalized = report_type.lower()
        if normalized not in supported:
            raise HTTPException(status_code=422, detail=f"Unsupported financial report: {report_type}")
        start_dt = datetime.combine(start, datetime.min.time()) if start else None
        end_dt = datetime.combine(end, datetime.max.time()) if end else None
        all_transactions = self.db.query(FinancialTransaction)
        transactions = all_transactions.filter(
            FinancialTransaction.status == FinancialTransactionStatus.COMPLETED
        )
        if start_dt:
            transactions = transactions.filter(FinancialTransaction.transaction_date >= start_dt)
            all_transactions = all_transactions.filter(FinancialTransaction.transaction_date >= start_dt)
        if end_dt:
            transactions = transactions.filter(FinancialTransaction.transaction_date <= end_dt)
            all_transactions = all_transactions.filter(FinancialTransaction.transaction_date <= end_dt)
        bookings = self.db.query(Booking)
        if start_dt:
            bookings = bookings.filter(Booking.created_at >= start_dt)
        if end_dt:
            bookings = bookings.filter(Booking.created_at <= end_dt)

        rows: list[dict] = []
        totals: dict[str, Decimal] = {}
        if normalized in {"revenue", "booking-profitability", "destination-profitability", "tour-profitability"}:
            for booking in bookings.all():
                costs = Decimal(self.db.query(func.coalesce(func.sum(TripItem.total_price), 0)).filter(TripItem.booking_id == booking.id).scalar() or 0)
                rows.append({
                    "booking_id": str(booking.id),
                    "booking_code": booking.booking_code,
                    "package_id": str(booking.package_id) if booking.package_id else None,
                    "destination_id": str(booking.package.destination_id) if booking.package and booking.package.destination_id else None,
                    "revenue": booking.total_amount,
                    "direct_cost": costs,
                    "gross_profit": booking.total_amount - costs,
                    "customer_id": str(booking.customer_id),
                })
            totals = {"revenue": sum((row["revenue"] for row in rows), Decimal(0)), "direct_cost": sum((row["direct_cost"] for row in rows), Decimal(0))}
            totals["gross_profit"] = totals["revenue"] - totals["direct_cost"]
        elif normalized == "collections":
            rows = [{"transaction_id": str(item.id), "booking_id": str(item.booking_id) if item.booking_id else None, "customer_id": str(item.customer_id) if item.customer_id else None, "amount": item.amount, "payment_method": item.payment_method.value if item.payment_method else None, "transaction_date": item.transaction_date.isoformat()} for item in transactions.filter(FinancialTransaction.category == FinancialTransactionCategory.BOOKING_PAYMENT).all()]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        elif normalized == "outstanding":
            rows = [
                {
                    "booking_id": str(item.id),
                    "booking_code": item.booking_code,
                    "customer_id": str(item.customer_id),
                    "total_amount": item.total_amount,
                    "paid_amount": item.paid_amount,
                    "outstanding": item.due_amount,
                }
                for item in bookings.filter(
                    Booking.due_amount > 0,
                    Booking.status.notin_(NON_COLLECTABLE_BOOKING_STATUSES),
                ).all()
            ]
            totals = {"outstanding": sum((row["outstanding"] for row in rows), Decimal(0))}
        elif normalized in {"expenses", "vendor-payments", "wallet-transactions"}:
            transaction_category = {"expenses": FinancialTransactionCategory.ADJUSTMENT, "vendor-payments": FinancialTransactionCategory.VENDOR_PAYMENT}.get(normalized)
            if normalized == "vendor-payments":
                query = all_transactions.filter(
                    FinancialTransaction.category == FinancialTransactionCategory.VENDOR_PAYMENT,
                    FinancialTransaction.status.in_([FinancialTransactionStatus.COMPLETED, FinancialTransactionStatus.REVERSED]),
                )
            elif transaction_category:
                query = transactions.filter(FinancialTransaction.category == transaction_category)
            else:
                query = all_transactions.filter(FinancialTransaction.category.in_([FinancialTransactionCategory.WALLET_CREDIT, FinancialTransactionCategory.WALLET_DEBIT, FinancialTransactionCategory.ADJUSTMENT]))
            rows = [{"transaction_id": str(item.id), "amount": item.amount, "status": item.status.value, "customer_id": str(item.customer_id) if item.customer_id else None, "vendor_id": str(item.vendor_id) if item.vendor_id else None, "booking_id": str(item.booking_id) if item.booking_id else None, "category": item.category, "payment_method": item.payment_method.value if item.payment_method else None, "transaction_date": item.transaction_date.isoformat(), "description": item.description} for item in query.all()]
            totals = {"amount": sum((row["amount"] for row in rows if row["status"] == FinancialTransactionStatus.COMPLETED.value), Decimal(0))}
        elif normalized == "payment-method":
            grouped = self.db.query(FinancialTransaction.payment_method, func.sum(FinancialTransaction.amount)).filter(FinancialTransaction.status == FinancialTransactionStatus.COMPLETED).group_by(FinancialTransaction.payment_method).all()
            rows = [{"payment_method": method.value if method else None, "amount": Decimal(amount or 0)} for method, amount in grouped]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        else:
            group_expr = extract("year", FinancialTransaction.transaction_date) if normalized == "yearly" else extract("month", FinancialTransaction.transaction_date)
            grouped = transactions.with_entities(group_expr.label("period"), func.sum(FinancialTransaction.amount)).group_by(group_expr).order_by(group_expr).all()
            rows = [{"period": int(period), "amount": Decimal(amount or 0)} for period, amount in grouped]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        return FinancialReportResponse(report_type=normalized, start_date=start.isoformat() if start else None, end_date=end.isoformat() if end else None, rows=rows, totals=totals)
