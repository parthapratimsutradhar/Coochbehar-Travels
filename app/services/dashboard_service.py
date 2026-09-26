from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.core.enums import AccountRole, BookingStatus
from app.models.account import Account
from app.models.booking import Booking
from app.models.destination import Destination
from app.models.enquiry import Enquiry
from app.models.hotel import Hotel
from app.models.review import Review
from app.models.tour_package import TourPackage
from app.models.vehicle import Vehicle
from app.repository.dashboard_repo import DashboardRepository
from app.schemas.analytics import SuperAdminDashboardResponse
from app.schemas.dashboard import DashboardResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DashboardRepository(db)

    def get_super_admin_dashboard(self) -> SuperAdminDashboardResponse:
        today = date.today()
        todays_metrics = self.repo.get_todays_metrics()
        future_metrics = self.repo.get_future_business_metrics()
        pipeline_metrics = self.repo.get_pipeline_metrics()
        year_overview = self.repo.get_period_overview(year=today.year)
        month_overview = self.repo.get_period_overview(year=today.year, month=today.month)

        return SuperAdminDashboardResponse(
            today=todays_metrics,
            future_business=future_metrics,
            pipeline=pipeline_metrics,
            current_year=year_overview,
            current_month=month_overview,
        )

    @staticmethod
    def _safe_percentage(current_value: Decimal | float | int, previous_value: Decimal | float | int) -> float:
        if previous_value in (None, 0):
            return 0.0
        return round(((float(current_value) - float(previous_value)) / float(previous_value)) * 100, 2)

    def _month_range(self, year: int, month: int) -> tuple[date, date]:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        return start, end

    @staticmethod
    def _datetime_range(start: date, end: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc),
        )

    @staticmethod
    def _get_booking_destination(booking: Booking) -> Destination | None:
        enquiry = booking.enquiry
        return (
            (enquiry.destination_ref if enquiry else None)
            or (booking.package.destination if booking.package else None)
            or (enquiry.package.destination if enquiry and enquiry.package else None)
        )

    def _get_monthly_history(self, months: int = 6) -> list[dict[str, int | str]]:
        history: list[dict[str, int | str]] = []
        current_month = datetime.now(timezone.utc).date().replace(day=1)

        for offset in range(months - 1, -1, -1):
            target_year = current_month.year
            target_month = current_month.month - offset
            while target_month <= 0:
                target_year -= 1
                target_month += 12
            while target_month > 12:
                target_year += 1
                target_month -= 12

            start_day, end_day = self._datetime_range(*self._month_range(target_year, target_month))
            month_revenue = self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
                Booking.created_at >= start_day,
                Booking.created_at < end_day,
            ).scalar() or Decimal(0)

            history.append({
                "month": datetime(target_year, target_month, 1).strftime("%b"),
                "revenue": int(month_revenue),
            })

        return history

    def get_dashboard_payload(self) -> DashboardResponse:
        today = datetime.now(timezone.utc).date()
        today_start, tomorrow_start = self._datetime_range(today, today + timedelta(days=1))

        all_bookings = self.db.query(Booking).all()
        today_bookings = self.db.query(Booking).filter(
            Booking.created_at >= today_start,
            Booking.created_at < tomorrow_start,
        ).all()
        total_revenue = sum((booking.total_amount for booking in all_bookings), Decimal(0))
        total_bookings_count = len(all_bookings)
        today_revenue = sum((booking.total_amount for booking in today_bookings), Decimal(0))

        customer_count = self.db.query(Account).filter(Account.role == AccountRole.CUSTOMER).count()
        active_trip_count = self.db.query(Booking).filter(
            Booking.status.in_([
                BookingStatus.CONFIRMED,
                BookingStatus.PARTIALLY_PAID,
                BookingStatus.FULLY_PAID,
                BookingStatus.TRAVELLED,
            ])
        ).count()

        pending_actions = self.db.query(Booking).filter(
            Booking.due_amount > 0,
            Booking.status.notin_([
                BookingStatus.CANCELLED,
                BookingStatus.COMPLETED,
                BookingStatus.REFUNDED,
            ]),
        ).count()

        hotel_count = self.db.query(Hotel).count()
        tour_package_count = self.db.query(TourPackage).count()
        bus_route_count = self.db.query(Vehicle).count()
        average_rating = self.db.query(func.coalesce(func.avg(Review.rating), 0)).scalar() or 0.0

        monthly_history = self._get_monthly_history()
        current_month_revenue = monthly_history[-1]["revenue"]
        previous_month_revenue = monthly_history[-2]["revenue"] if len(monthly_history) > 1 else 0
        current_month_growth = self._safe_percentage(current_month_revenue, previous_month_revenue)

        average_monthly_revenue = int(sum(item["revenue"] for item in monthly_history) / len(monthly_history)) if monthly_history else 0
        peak_month = max(monthly_history, key=lambda item: item["revenue"], default={"month": "N/A", "revenue": 0})

        current_year_start, current_year_end = self._datetime_range(
            date(today.year, 1, 1), date(today.year + 1, 1, 1)
        )
        previous_year_start, previous_year_end = self._datetime_range(
            date(today.year - 1, 1, 1), date(today.year, 1, 1)
        )
        current_year_revenue = self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
            Booking.created_at >= current_year_start,
            Booking.created_at < current_year_end,
        ).scalar() or Decimal(0)
        previous_year_revenue = self.db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
            Booking.created_at >= previous_year_start,
            Booking.created_at < previous_year_end,
        ).scalar() or Decimal(0)
        yoy_growth = self._safe_percentage(current_year_revenue, previous_year_revenue)

        current_month_start, current_month_end = self._month_range(today.year, today.month)
        last_month_year = current_month_start.year if current_month_start.month > 1 else current_month_start.year - 1
        last_month_month = current_month_start.month - 1 if current_month_start.month > 1 else 12
        last_month_start, last_month_end = self._month_range(last_month_year, last_month_month)
        last_month_start, last_month_end = self._datetime_range(last_month_start, last_month_end)
        current_month_start, current_month_end = self._datetime_range(current_month_start, current_month_end)
        comparison_period = f"vs {last_month_start.strftime('%B %Y')}"

        last_month_bookings = self.db.query(Booking).filter(
            Booking.created_at >= last_month_start,
            Booking.created_at < last_month_end,
        ).count()
        current_month_bookings = self.db.query(Booking).filter(
            Booking.created_at >= current_month_start,
            Booking.created_at < current_month_end,
        ).count()
        total_booking_growth = self._safe_percentage(current_month_bookings, last_month_bookings)

        previous_month_customer_count = self.db.query(Account).filter(
            Account.role == AccountRole.CUSTOMER,
            Account.created_at >= last_month_start,
            Account.created_at < last_month_end,
        ).count()
        current_month_customer_count = self.db.query(Account).filter(
            Account.role == AccountRole.CUSTOMER,
            Account.created_at >= current_month_start,
            Account.created_at < current_month_end,
        ).count()
        customer_growth = self._safe_percentage(current_month_customer_count, previous_month_customer_count)

        active_trip_growth = self._safe_percentage(active_trip_count, max(1, active_trip_count)) if active_trip_count else 0.0

        package_destination = aliased(Destination)
        enquiry_destination = aliased(Destination)
        enquiry_package = aliased(TourPackage)
        enquiry_package_destination = aliased(Destination)
        destination_id = func.coalesce(
            enquiry_destination.id,
            package_destination.id,
            enquiry_package_destination.id,
        )
        destination_name = func.coalesce(
            enquiry_destination.name,
            package_destination.name,
            enquiry_package_destination.name,
        )
        destination_image = func.coalesce(
            enquiry_destination.image_url,
            package_destination.image_url,
            enquiry_package_destination.image_url,
        )
        destination_rows = (
            self.db.query(
                destination_name.label("name"),
                destination_image.label("image_url"),
                func.count(Booking.id).label("booking_count"),
            )
            .outerjoin(TourPackage, Booking.package_id == TourPackage.id)
            .outerjoin(package_destination, TourPackage.destination_id == package_destination.id)
            .outerjoin(Enquiry, Booking.enquiry_id == Enquiry.id)
            .outerjoin(enquiry_destination, Enquiry.destination_id == enquiry_destination.id)
            .outerjoin(enquiry_package, Enquiry.package_id == enquiry_package.id)
            .outerjoin(
                enquiry_package_destination,
                enquiry_package.destination_id == enquiry_package_destination.id,
            )
            .filter(destination_id.is_not(None))
            .group_by(destination_id, destination_name, destination_image)
            .order_by(func.count(Booking.id).desc())
            .limit(5)
            .all()
        )

        top_destinations = [
            {
                "rank": index + 1,
                "name": row.name,
                "image_url": row.image_url,
                "total_bookings": int(row.booking_count),
            }
            for index, row in enumerate(destination_rows)
        ]

        recent_rows = self.db.query(Booking).order_by(Booking.created_at.desc()).limit(6).all()
        recent_bookings = []
        for booking in recent_rows:
            buyer_name = booking.customer.name if booking.customer else "Customer"
            initials = "".join(part[0].upper() for part in buyer_name.split()[:2]) if buyer_name else "C"
            destination = self._get_booking_destination(booking)
            destination_name = destination.name if destination else "N/A"
            package_name = booking.package.title if booking.package else "Custom Tour"
            recent_bookings.append({
                "booking_id": booking.booking_code,
                "customer": {"name": buyer_name, "initials": initials},
                "destination": destination_name,
                "package_name": package_name,
                "amount": int(booking.total_amount),
                "currency": "INR",
                "booking_date": booking.created_at.date().isoformat(),
                "status": booking.status.value,
            })

        payload = {
            "summary": {
                "today_bookings": len(today_bookings),
                "today_revenue": int(today_revenue),
                "pending_actions": pending_actions,
                "total_revenue": {
                    "amount": int(total_revenue),
                    "currency": "INR",
                    "growth_percentage": current_month_growth,
                    "comparison_period": comparison_period,
                },
                "total_bookings": {
                    "count": total_bookings_count,
                    "growth_percentage": total_booking_growth,
                    "comparison_period": comparison_period,
                },
                "registered_users": {
                    "count": customer_count,
                    "growth_percentage": customer_growth,
                    "comparison_period": comparison_period,
                },
                "active_trips": {
                    "count": active_trip_count,
                    "growth_percentage": active_trip_growth,
                    "comparison_period": comparison_period,
                },
            },
            "platform_metrics": {
                "hotels_listed": hotel_count,
                "tour_packages": tour_package_count,
                "bus_routes": bus_route_count,
                "average_rating": round(float(average_rating), 1),
            },
            "revenue_analytics": {
                "current_month_revenue": current_month_revenue,
                "growth_this_month_percentage": current_month_growth,
                "average_monthly_revenue": average_monthly_revenue,
                "peak_month": peak_month["month"],
                "yoy_growth_percentage": yoy_growth,
                "monthly_history": [{"month": item["month"], "revenue": item["revenue"]} for item in monthly_history],
            },
            "top_destinations": top_destinations,
            "recent_bookings": recent_bookings,
        }
        return DashboardResponse.model_validate(payload)
