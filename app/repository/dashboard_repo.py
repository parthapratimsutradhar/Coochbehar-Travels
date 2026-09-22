from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.enums import AccountRole, BookingStatus, QuotationStatus
from app.models.account import Account
from app.models.booking import Booking
from app.models.financial_transaction import FinancialTransaction
from app.models.enquiry import Enquiry
from app.models.quotation import Quotation
from app.models.trip_items import TripItem


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_todays_metrics(self) -> dict:
        today = date.today()
        new_enquiries = self.db.execute(
            select(func.count()).select_from(Enquiry).where(func.date(Enquiry.created_at) == today)
        ).scalar_one()

        new_bookings = self.db.execute(
            select(func.count()).select_from(Booking).where(func.date(Booking.created_at) == today)
        ).scalar_one()

        revenue = self.db.execute(
            select(func.coalesce(func.sum(Booking.total_amount), 0)).where(func.date(Booking.created_at) == today)
        ).scalar_one()

        collections = self.db.execute(
            select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
                func.date(FinancialTransaction.transaction_date) == today,
                FinancialTransaction.transaction_type == "BOOKING_PAYMENT",
                FinancialTransaction.status == "POSTED",
            )
        ).scalar_one()

        pending = self.db.execute(
            select(func.coalesce(func.sum(Booking.due_amount), 0)).where(func.date(Booking.created_at) == today)
        ).scalar_one()

        return {
            "new_enquiries": new_enquiries,
            "new_bookings": new_bookings,
            "revenue": Decimal(revenue),
            "collections": Decimal(collections),
            "pending_collections": Decimal(pending),
        }

    def get_future_business_metrics(self) -> dict:
        # Confirmed future bookings
        confirmed_statuses = [
            BookingStatus.CONFIRMED,
            BookingStatus.PARTIALLY_PAID,
            BookingStatus.FULLY_PAID,
        ]
        stmt_rev = select(func.coalesce(func.sum(Booking.total_amount), 0)).where(
            Booking.status.in_(confirmed_statuses)
        )
        confirmed_revenue = Decimal(self.db.execute(stmt_rev).scalar_one())

        stmt_pending = select(func.coalesce(func.sum(Booking.due_amount), 0)).where(
            Booking.status.in_(confirmed_statuses)
        )
        pending_collection = Decimal(self.db.execute(stmt_pending).scalar_one())

        stmt_cost = select(func.coalesce(func.sum(TripItem.total_price), 0)).where(
            TripItem.booking_id.is_not(None)
        )
        projected_cost = Decimal(self.db.execute(stmt_cost).scalar_one())

        projected_profit = max(Decimal(0), confirmed_revenue - projected_cost)

        return {
            "confirmed_revenue": confirmed_revenue,
            "projected_cost": projected_cost,
            "projected_profit": projected_profit,
            "pending_collection": pending_collection,
        }

    def get_pipeline_metrics(self) -> dict:
        enquiries_count = self.db.execute(select(func.count()).select_from(Enquiry)).scalar_one()
        quotations_count = self.db.execute(select(func.count()).select_from(Quotation)).scalar_one()
        tentative_count = self.db.execute(
            select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.TENTATIVE)
        ).scalar_one()
        confirmed_count = self.db.execute(
            select(func.count()).select_from(Booking).where(
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PARTIALLY_PAID, BookingStatus.FULLY_PAID])
            )
        ).scalar_one()

        conversion_rate = (
            round((confirmed_count / enquiries_count) * 100, 2)
            if enquiries_count > 0
            else 0.0
        )

        return {
            "enquiries_count": enquiries_count,
            "quotations_count": quotations_count,
            "tentative_bookings_count": tentative_count,
            "confirmed_bookings_count": confirmed_count,
            "conversion_rate": conversion_rate,
        }

    def get_period_overview(self, year: int, month: int | None = None) -> dict:
        stmt_booking = select(Booking).where(extract("year", Booking.created_at) == year)
        if month is not None:
            stmt_booking = stmt_booking.where(extract("month", Booking.created_at) == month)

        bookings = self.db.execute(stmt_booking).scalars().all()
        revenue = sum((b.total_amount for b in bookings), Decimal(0))
        total_bookings = len(bookings)

        # Direct costs
        booking_ids = [b.id for b in bookings]
        if booking_ids:
            stmt_cost = select(func.coalesce(func.sum(TripItem.total_price), 0)).where(
                TripItem.booking_id.in_(booking_ids)
            )
            direct_cost = Decimal(self.db.execute(stmt_cost).scalar_one())
        else:
            direct_cost = Decimal(0)

        gross_profit = revenue - direct_cost
        profit_margin = round(float((gross_profit / revenue) * 100), 2) if revenue > Decimal(0) else 0.0

        # General business expenses
        stmt_exp = select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
            FinancialTransaction.transaction_type == "EXPENSE",
            FinancialTransaction.status == "POSTED",
            extract("year", FinancialTransaction.transaction_date) == year,
        )
        if month is not None:
            stmt_exp = stmt_exp.where(extract("month", FinancialTransaction.transaction_date) == month)
        general_expenses = Decimal(self.db.execute(stmt_exp).scalar_one())

        net_profit = gross_profit - general_expenses

        # Customer count
        stmt_cust = select(func.count()).select_from(Account).where(
            Account.role == AccountRole.CUSTOMER,
            extract("year", Account.created_at) == year,
        )
        if month is not None:
            stmt_cust = stmt_cust.where(extract("month", Account.created_at) == month)
        total_customers = self.db.execute(stmt_cust).scalar_one()

        return {
            "revenue": revenue,
            "direct_cost": direct_cost,
            "gross_profit": gross_profit,
            "profit_margin": profit_margin,
            "general_expenses": general_expenses,
            "net_profit": net_profit,
            "total_bookings": total_bookings,
            "total_customers": total_customers,
        }
