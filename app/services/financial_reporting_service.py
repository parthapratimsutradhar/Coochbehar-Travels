from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus, FinancialTransactionStatus, FinancialTransactionType, FinancialAccountOwnerType, FinancialAccountType
from app.models.booking import Booking
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.models.trip_items import TripItem
from app.schemas.financial_reports import FinancialDashboardResponse, FinancialReportResponse


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
            FinancialTransaction.status == FinancialTransactionStatus.POSTED
        )
        if transaction_type is not None:
            query = query.filter(FinancialTransaction.transaction_type == transaction_type)
        return Decimal(query.scalar() or 0)

    def dashboard(self) -> FinancialDashboardResponse:
        revenue = Decimal(self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
            Booking.status != BookingStatus.CANCELLED
        ).scalar() or 0)
        collections = self._sum_transactions(FinancialTransactionType.BOOKING_PAYMENT)
        expenses = self._sum_transactions(FinancialTransactionType.EXPENSE)
        direct_cost = Decimal(self.db.query(func.coalesce(func.sum(TripItem.total_price), 0)).filter(TripItem.booking_id.is_not(None)).scalar() or 0)
        customer_outstanding = Decimal(self.db.query(func.coalesce(func.sum(Booking.due_amount), 0)).filter(
            Booking.status != BookingStatus.CANCELLED
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

    def _wallet_entry_sum(self, column: str) -> Decimal:
        value = getattr(FinancialTransactionEntry, column)
        result = self.db.query(func.coalesce(func.sum(value), 0)).join(
            FinancialAccount, FinancialAccount.id == FinancialTransactionEntry.account_id
        ).join(
            FinancialTransaction, FinancialTransaction.id == FinancialTransactionEntry.transaction_id
        ).filter(
            FinancialAccount.owner_type == FinancialAccountOwnerType.CUSTOMER,
            FinancialAccount.account_type == FinancialAccountType.LIABILITY,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
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
            FinancialTransaction.status == FinancialTransactionStatus.POSTED
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
            rows = [{"transaction_id": str(item.id), "booking_id": str(item.booking_id) if item.booking_id else None, "customer_id": str(item.customer_id) if item.customer_id else None, "amount": item.amount, "payment_method": item.payment_method.value if item.payment_method else None, "transaction_date": item.transaction_date.isoformat()} for item in transactions.filter(FinancialTransaction.transaction_type == FinancialTransactionType.BOOKING_PAYMENT).all()]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        elif normalized == "outstanding":
            rows = [{"booking_id": str(item.id), "booking_code": item.booking_code, "customer_id": str(item.customer_id), "total_amount": item.total_amount, "paid_amount": item.paid_amount, "outstanding": item.due_amount} for item in bookings.filter(Booking.due_amount > 0).all()]
            totals = {"outstanding": sum((row["outstanding"] for row in rows), Decimal(0))}
        elif normalized in {"expenses", "vendor-payments", "wallet-transactions"}:
            transaction_type = {"expenses": FinancialTransactionType.EXPENSE, "vendor-payments": FinancialTransactionType.VENDOR_PAYMENT}.get(normalized)
            if normalized == "vendor-payments":
                query = all_transactions.filter(
                    FinancialTransaction.transaction_type == FinancialTransactionType.VENDOR_PAYMENT,
                    FinancialTransaction.status.in_([FinancialTransactionStatus.POSTED, FinancialTransactionStatus.REVERSED]),
                )
            elif transaction_type:
                query = transactions.filter(FinancialTransaction.transaction_type == transaction_type)
            else:
                query = all_transactions.filter(FinancialTransaction.transaction_type.in_([FinancialTransactionType.WALLET_CREDIT, FinancialTransactionType.WALLET_DEBIT, FinancialTransactionType.ADJUSTMENT]))
            rows = [{"transaction_id": str(item.id), "amount": item.amount, "status": item.status.value, "customer_id": str(item.customer_id) if item.customer_id else None, "vendor_id": str(item.vendor_id) if item.vendor_id else None, "booking_id": str(item.booking_id) if item.booking_id else None, "category": item.category, "payment_method": item.payment_method.value if item.payment_method else None, "transaction_date": item.transaction_date.isoformat(), "description": item.description} for item in query.all()]
            totals = {"amount": sum((row["amount"] for row in rows if row["status"] == FinancialTransactionStatus.POSTED.value), Decimal(0))}
        elif normalized == "payment-method":
            grouped = self.db.query(FinancialTransaction.payment_method, func.sum(FinancialTransaction.amount)).filter(FinancialTransaction.status == FinancialTransactionStatus.POSTED).group_by(FinancialTransaction.payment_method).all()
            rows = [{"payment_method": method.value if method else None, "amount": Decimal(amount or 0)} for method, amount in grouped]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        else:
            group_expr = extract("year", FinancialTransaction.transaction_date) if normalized == "yearly" else extract("month", FinancialTransaction.transaction_date)
            grouped = transactions.with_entities(group_expr.label("period"), func.sum(FinancialTransaction.amount)).group_by(group_expr).order_by(group_expr).all()
            rows = [{"period": int(period), "amount": Decimal(amount or 0)} for period, amount in grouped]
            totals = {"amount": sum((row["amount"] for row in rows), Decimal(0))}
        return FinancialReportResponse(report_type=normalized, start_date=start.isoformat() if start else None, end_date=end.isoformat() if end else None, rows=rows, totals=totals)
