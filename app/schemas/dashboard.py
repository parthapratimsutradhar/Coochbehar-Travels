from app.schemas.base import SchemaBase


class TotalRevenueMetric(SchemaBase):
    amount: int
    currency: str
    growth_percentage: float
    comparison_period: str


class GrowthMetric(SchemaBase):
    count: int
    growth_percentage: float
    comparison_period: str


class SummaryMetrics(SchemaBase):
    today_bookings: int
    today_revenue: int
    pending_actions: int
    total_revenue: TotalRevenueMetric
    total_bookings: GrowthMetric
    registered_users: GrowthMetric
    active_trips: GrowthMetric


class PlatformMetrics(SchemaBase):
    hotels_listed: int
    tour_packages: int
    bus_routes: int
    average_rating: float


class MonthlyRevenue(SchemaBase):
    month: str
    revenue: int


class RevenueAnalytics(SchemaBase):
    current_month_revenue: int
    growth_this_month_percentage: float
    average_monthly_revenue: int
    peak_month: str
    yoy_growth_percentage: float
    monthly_history: list[MonthlyRevenue]


class TopDestination(SchemaBase):
    rank: int
    name: str
    icon: str
    total_bookings: int


class CustomerSummary(SchemaBase):
    name: str
    initials: str


class RecentBooking(SchemaBase):
    booking_id: str
    customer: CustomerSummary
    destination: str
    package_name: str
    amount: int
    currency: str
    booking_date: str
    status: str


class DashboardResponse(SchemaBase):
    summary: SummaryMetrics
    platform_metrics: PlatformMetrics
    revenue_analytics: RevenueAnalytics
    top_destinations: list[TopDestination]
    recent_bookings: list[RecentBooking]
