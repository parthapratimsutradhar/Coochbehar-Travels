from decimal import Decimal

from pydantic import Field

from app.schemas.base import SchemaBase


class FinancialDashboardResponse(SchemaBase):
    total_revenue: Decimal = Decimal(0)
    total_collections: Decimal = Decimal(0)
    total_expenses: Decimal = Decimal(0)
    gross_profit: Decimal = Decimal(0)
    net_profit: Decimal = Decimal(0)
    customer_outstanding: Decimal = Decimal(0)
    vendor_payables: Decimal = Decimal(0)
    confirmed_future_revenue: Decimal = Decimal(0)
    projected_future_cost: Decimal = Decimal(0)
    projected_future_profit: Decimal = Decimal(0)
    future_customer_collections: Decimal = Decimal(0)
    future_customer_outstanding: Decimal = Decimal(0)
    expected_vendor_payments: Decimal = Decimal(0)
    customer_wallet_balances: Decimal = Decimal(0)
    wallet_credits: Decimal = Decimal(0)
    wallet_debits: Decimal = Decimal(0)


class FinancialReportResponse(SchemaBase):
    report_type: str
    start_date: str | None = None
    end_date: str | None = None
    rows: list[dict] = Field(default_factory=list)
    totals: dict[str, Decimal] = Field(default_factory=dict)


class FinancialStatisticsResponse(SchemaBase):
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_income: str | None = None
    total_expenses: str | None = None
    referral_income: str | None = None
    net_profit_loss: str | None = None
