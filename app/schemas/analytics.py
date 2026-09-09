from decimal import Decimal
from pydantic import Field
from app.schemas.base import SchemaBase


class TodaysBusinessMetrics(SchemaBase):
    new_enquiries: int = 0
    new_bookings: int = 0
    revenue: Decimal = Decimal(0)
    collections: Decimal = Decimal(0)
    pending_collections: Decimal = Decimal(0)


class FutureBusinessMetrics(SchemaBase):
    confirmed_revenue: Decimal = Decimal(0)
    projected_cost: Decimal = Decimal(0)
    projected_profit: Decimal = Decimal(0)
    pending_collection: Decimal = Decimal(0)


class BookingPipelineMetrics(SchemaBase):
    enquiries_count: int = 0
    quotations_count: int = 0
    tentative_bookings_count: int = 0
    confirmed_bookings_count: int = 0
    conversion_rate: float = 0.0


class PeriodBusinessOverview(SchemaBase):
    revenue: Decimal = Decimal(0)
    direct_cost: Decimal = Decimal(0)
    gross_profit: Decimal = Decimal(0)
    profit_margin: float = 0.0
    general_expenses: Decimal = Decimal(0)
    net_profit: Decimal = Decimal(0)
    total_bookings: int = 0
    total_customers: int = 0


class SuperAdminDashboardResponse(SchemaBase):
    today: TodaysBusinessMetrics
    future_business: FutureBusinessMetrics
    pipeline: BookingPipelineMetrics
    current_year: PeriodBusinessOverview
    current_month: PeriodBusinessOverview
