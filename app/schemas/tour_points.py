import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PointTransactionType, TourType
from app.schemas.base import SchemaBase
from app.schemas.pagination import PaginationMeta


class TourPointConfigurationUpdate(SchemaBase):
    amount_per_point: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="INR value required to earn one point. For example, 10000 means ₹10,000 per point.",
        examples=[10000.00],
    )


class TourPointConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Configuration record identifier.")
    tour_type: TourType = Field(description="Tour category this rate applies to.")
    amount_per_point: Decimal = Field(description="INR amount required to earn one point.", examples=[10000.00])
    updated_at: datetime = Field(description="Timestamp of the latest configuration update.")
    updated_by_account_id: uuid.UUID | None = Field(
        default=None,
        description="Admin account that made the latest update, if available.",
    )


class TourPointConfigurationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Immutable configuration history record identifier.")
    configuration_id: uuid.UUID | None = Field(description="Current configuration record, if it still exists.")
    tour_type: TourType = Field(description="Tour category whose rate changed.")
    previous_amount_per_point: Decimal | None = Field(description="Rate before this change; null for the initial rate.")
    amount_per_point: Decimal = Field(description="New INR amount required to earn one point.")
    changed_by_account_id: uuid.UUID | None = Field(description="Admin account that made the change, if available.")
    changed_by_account_profile_pic: str | None = Field(default=None, description="Admin profile picture URL, if available.")
    changed_by_account_name: str | None = Field(
        default=None,
        description="Admin name, or System for an automatically initialized default rate.",
    )
    changed_by_account_email: str | None = Field(default=None, description="Email of the admin who made the change, if available.")
    changed_by_account_mobile: str | None = Field(default=None, description="Mobile number of the admin who made the change, if available.")
    changed_at: datetime = Field(description="When this configuration change was recorded.")


class TourPointTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Immutable point transaction identifier.")
    booking_id: uuid.UUID | None = Field(description="Related booking, if this transaction came from a booking.")
    package_id: uuid.UUID | None = Field(description="Related tour package, if available.")
    booking_code: str | None = Field(description="Booking reference captured when the transaction was created.")
    tour_title: str | None = Field(description="Tour title captured when the transaction was created.")
    transaction_type: PointTransactionType = Field(description="Earn, reversal, or manual adjustment event.")
    points: Decimal = Field(description="Signed point delta; reversals are negative.", examples=[2.5, -2.5])
    balance_before: Decimal = Field(description="Customer balance immediately before this transaction.")
    balance_after: Decimal = Field(description="Customer balance immediately after this transaction.")
    amount_per_point: Decimal | None = Field(description="Rate snapshot used for this booking award, if applicable.")
    reason: str = Field(description="Audit description for the point change.")
    created_at: datetime = Field(description="When the transaction was recorded.")


class AdminTourPointTransactionResponse(TourPointTransactionResponse):
    customer_id: uuid.UUID
    customer_code: str
    customer_name: str
    customer_email: str | None
    customer_mobile: str | None
    customer_profile_pic: str | None


class PublicUserRankingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int = Field(description="Customer position ordered by point balance, highest first.", examples=[1])
    customer_name: str = Field(description="Customer display name shown in the public ranking.", examples=["Asha Das"])
    customer_profile_picture: str | None = Field(
        default=None,
        description="Public profile picture URL, if the customer has one.",
        examples=["https://cdn.example.com/profiles/customer.jpg"],
    )
    customer_joined_at: datetime = Field(
        description="Date and time the customer registered.",
        examples=["2025-04-15T09:30:00Z"],
    )
    point_balance: Decimal = Field(
        description="Customer's current point balance.",
        examples=[12.5],
    )


class CustomerRankPositionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int = Field(description="Current rank among active customers.", examples=[12])
    page_number: int = Field(description="One-based leaderboard page containing the customer.", examples=[2])
    page_size: int = Field(description="Number of ranking entries per leaderboard page.", examples=[10])
    point_balance: Decimal = Field(description="Customer's current point balance.", examples=[12.5])


class AdminUserRankingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int = Field(description="Customer rank ordered by current point balance, highest first.")
    customer_id: uuid.UUID = Field(description="Internal customer account identifier.")
    customer_code: str = Field(description="Customer account reference code.")
    customer_name: str = Field(description="Customer account name.")
    customer_profile_picture: str | None = Field(
        default=None,
        description="Customer profile picture URL, if available.",
    )
    points: Decimal = Field(description="Current point balance.")
    customer_joined_at: datetime = Field(description="Timestamp when the customer account was created.")
    money_spends: Decimal = Field(
        description="Net customer payments after wallet refunds, in INR.",
        examples=[1500.00],
    )


class CustomerPointsResponse(BaseModel):
    points_balance: Decimal
    rank: int
    transactions: list[TourPointTransactionResponse]
    transaction_pagination: PaginationMeta
