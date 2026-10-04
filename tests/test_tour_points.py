from decimal import Decimal
from datetime import date, datetime, time, timezone
import uuid

import app.models
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import (
    AccountRole,
    BookingSource,
    BookingStatus,
    EnquiryChannel,
    EnquiryType,
    FinancialAccountOwnerType,
    FinancialAccountType,
    FinancialTransactionCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    PointTransactionType,
    QuotationStatus,
    TourType,
)
from app.db.database import get_db
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.enquiry import Enquiry
from app.models.financial_account import FinancialAccount
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction_entry import FinancialTransactionEntry
from app.models.quotation import Quotation
from app.models.tour_package import TourPackage
from app.models.tour_departure import TourDeparture
from app.models.tour_point_transaction import TourPointTransaction
from app.models.tour_variant import TourVariant
from app.schemas.booking import BookingTravelerCreate, OfflineBookingCreate
from app.services.booking_service import BookingService
from app.services.quotation_service import QuotationService
from app.services.tour_points_service import TourPointsService
from app.main import fastapi_app as app
from app.utils.security import create_access_token


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def make_account(db, *, role: AccountRole, code: str, name: str) -> Account:
    account = Account(
        account_code=code,
        name=name,
        role=role,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def make_booking(db, customer: Account, *, tour_type: TourType, amount: Decimal) -> Booking:
    booking = Booking(
        booking_code=f"BK-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        booking_type=tour_type,
        source=BookingSource.WEBSITE,
        status=BookingStatus.TENTATIVE,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=amount,
        discount_amount=Decimal("0"),
        total_amount=amount,
        paid_amount=Decimal("0"),
        due_amount=amount,
        created_by=customer.id,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def test_cancellation_reverses_original_award_once_after_configuration_changes(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-POINTS-1", name="Customer One")
    admin = make_account(db, role=AccountRole.ADMIN, code="A-POINTS-1", name="Admin")
    service = TourPointsService(db)
    service.get_configurations()
    booking = make_booking(db, customer, tour_type=TourType.DOMESTIC, amount=Decimal("25000.00"))

    BookingService(db).update_booking_status(booking.id, BookingStatus.CONFIRMED)
    db.refresh(customer)
    db.refresh(booking)
    assert customer.points_balance == Decimal("2.5000")
    assert booking.points_awarded == Decimal("2.5000")
    assert booking.points_amount_per_point == Decimal("10000.00")

    config = service.repo.get_configuration(TourType.DOMESTIC)
    service.update_configuration(TourType.DOMESTIC, Decimal("5000.00"), admin.id)
    assert config.amount_per_point == Decimal("5000.00")

    booking_service = BookingService(db)
    booking_service.update_booking_status(booking.id, BookingStatus.CANCELLED)
    booking_service.update_booking_status(booking.id, BookingStatus.CANCELLED)
    db.refresh(customer)

    transactions = db.execute(
        select(TourPointTransaction)
        .where(TourPointTransaction.booking_id == booking.id)
        .order_by(TourPointTransaction.created_at)
    ).scalars().all()
    assert customer.points_balance == Decimal("0.0000")
    assert len(transactions) == 2
    assert transactions[0].transaction_type == PointTransactionType.BOOKING_EARNED
    assert transactions[0].points == Decimal("2.5000")
    assert transactions[1].transaction_type == PointTransactionType.BOOKING_REVERSED
    assert transactions[1].points == Decimal("-2.5000")
    assert transactions[1].amount_per_point == Decimal("10000.00")


def test_international_booking_awards_decimal_points_from_its_own_rate(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-POINTS-2", name="Customer Two")
    admin = make_account(db, role=AccountRole.ADMIN, code="A-POINTS-2", name="Admin Two")
    service = TourPointsService(db)
    service.get_configurations()
    service.update_configuration(TourType.INTERNATIONAL, Decimal("8000.00"), admin.id)
    booking = make_booking(db, customer, tour_type=TourType.INTERNATIONAL, amount=Decimal("30000.00"))

    BookingService(db).update_booking_status(booking.id, BookingStatus.CONFIRMED)
    db.refresh(customer)
    db.refresh(booking)

    assert customer.points_balance == Decimal("3.7500")
    assert booking.points_awarded == Decimal("3.7500")
    assert booking.points_amount_per_point == Decimal("8000.00")


def test_idempotency_key_returns_existing_booking_without_double_credit(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-POINTS-3", name="Customer Three")
    staff = make_account(db, role=AccountRole.STAFF, code="S-POINTS-1", name="Staff")
    payload = OfflineBookingCreate(
        customer_id=customer.id,
        adult_count=1,
        child_count=0,
        senior_count=0,
        total_selling_price=Decimal("25000.00"),
        advance_received=Decimal("0"),
    )
    service = BookingService(db)

    first = service.create_offline_booking(payload, staff, idempotency_key="request-123")
    second = service.create_offline_booking(payload, staff, idempotency_key="request-123")
    db.refresh(customer)

    tx_count = db.execute(
        select(func.count()).select_from(TourPointTransaction).where(
            TourPointTransaction.account_id == customer.id
        )
    ).scalar_one()
    assert first.id == second.id
    assert customer.points_balance == Decimal("2.5000")
    assert tx_count == 1


def create_departure(db, *, available_seats: int, total_seats: int = 5) -> TourDeparture:
    package = TourPackage(
        tour_code=f"TP-{uuid.uuid4().hex[:8]}",
        slug=f"tour-{uuid.uuid4().hex[:8]}",
        title="Departure test tour",
        type=TourType.DOMESTIC,
    )
    db.add(package)
    db.flush()
    variant = TourVariant(
        package_id=package.id,
        slug=f"variant-{uuid.uuid4().hex[:8]}",
        name="Standard",
        valid_from=date(2026, 1, 1),
        valid_to=date(2027, 12, 31),
        duration_days=3,
        duration_nights=2,
        list_price=Decimal("30000.00"),
        selling_price=Decimal("30000.00"),
    )
    db.add(variant)
    db.flush()
    departure = TourDeparture(
        variant_id=variant.id,
        departure_date=date(2026, 12, 15),
        total_seats=total_seats,
        available_seats=available_seats,
    )
    db.add(departure)
    db.commit()
    db.refresh(departure)
    return departure


def test_booking_reserves_and_restores_departure_seats_once(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-SEATS-1", name="Seat Customer")
    staff = make_account(db, role=AccountRole.STAFF, code="S-SEATS-1", name="Seat Staff")
    departure = create_departure(db, available_seats=5)
    payload = OfflineBookingCreate(
        customer_id=customer.id,
        departure_id=departure.id,
        adult_count=2,
        child_count=1,
        senior_count=0,
        total_selling_price=Decimal("30000.00"),
        travellers=[
            {"full_name": "Guest One"},
            {"full_name": "Guest Two"},
            {"full_name": "Guest Three"},
        ],
    )

    booking = BookingService(db).create_offline_booking(payload, staff)
    db.refresh(departure)
    db.refresh(booking)
    assert booking.departure_date == date(2026, 12, 15)
    assert booking.departure_seats_reserved == 3
    assert departure.available_seats == 2

    service = BookingService(db)
    service.update_booking_status(booking.id, BookingStatus.CANCELLED)
    service.update_booking_status(booking.id, BookingStatus.CANCELLED)
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 5
    assert booking.departure_seats_reserved == 0

    service.update_booking_status(booking.id, BookingStatus.CONFIRMED)
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 2
    assert booking.departure_seats_reserved == 3


def test_booking_with_insufficient_departure_seats_is_rejected_without_changes(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-SEATS-2", name="Seat Customer Two")
    staff = make_account(db, role=AccountRole.STAFF, code="S-SEATS-2", name="Seat Staff Two")
    departure = create_departure(db, available_seats=2)
    payload = OfflineBookingCreate(
        customer_id=customer.id,
        departure_id=departure.id,
        adult_count=2,
        child_count=1,
        senior_count=0,
        total_selling_price=Decimal("30000.00"),
    )

    with pytest.raises(HTTPException) as error:
        BookingService(db).create_offline_booking(payload, staff)

    db.refresh(departure)
    assert error.value.status_code == 409
    assert departure.available_seats == 2
    assert db.execute(select(func.count()).select_from(Booking)).scalar_one() == 0


def test_adding_and_removing_travellers_adjusts_seats_for_active_and_cancelled_bookings(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-SEATS-3", name="Seat Customer Three")
    staff = make_account(db, role=AccountRole.STAFF, code="S-SEATS-3", name="Seat Staff Three")
    departure = create_departure(db, available_seats=3, total_seats=3)
    payload = OfflineBookingCreate(
        customer_id=customer.id,
        departure_id=departure.id,
        adult_count=1,
        child_count=0,
        senior_count=0,
        total_selling_price=Decimal("10000.00"),
        travellers=[{"full_name": "First Guest"}],
    )
    service = BookingService(db)
    booking = service.create_offline_booking(payload, staff)
    db.refresh(departure)
    assert departure.available_seats == 2

    added = service.add_traveller(booking.id, BookingTravelerCreate(full_name="Second Guest"))
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 1
    assert booking.departure_seats_reserved == 2

    service.delete_traveller(booking.id, added.id)
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 2
    assert booking.departure_seats_reserved == 1

    service.update_booking_status(booking.id, BookingStatus.CANCELLED)
    cancelled_guest = service.add_traveller(
        booking.id,
        BookingTravelerCreate(full_name="Guest Added While Cancelled"),
    )
    db.refresh(departure)
    assert departure.available_seats == 3

    service.update_booking_status(booking.id, BookingStatus.CONFIRMED)
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 1
    assert booking.departure_seats_reserved == 2

    service.delete_traveller(booking.id, cancelled_guest.id)
    db.refresh(departure)
    db.refresh(booking)
    assert departure.available_seats == 2
    assert booking.departure_seats_reserved == 1


def test_accepting_quotation_reserves_departure_seats_for_travellers(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-QUOTE-SEAT", name="Quote Customer")
    departure = create_departure(db, available_seats=5)
    variant = db.get(TourVariant, departure.variant_id)
    travel_date = datetime.combine(departure.departure_date, time.min, tzinfo=timezone.utc)
    enquiry = Enquiry(
        enquiry_code=f"ENQ-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
        variant_id=variant.id,
        travel_date=departure.departure_date,
        adult_count=2,
        child_count=1,
        senior_count=0,
    )
    db.add(enquiry)
    db.flush()
    quotation = Quotation(
        quotation_code=f"QT-{uuid.uuid4().hex[:8]}",
        version=1,
        customer_id=customer.id,
        enquiry_id=enquiry.id,
        package_id=variant.package_id,
        variant_id=variant.id,
        departure_id=departure.id,
        tour_name="Departure test tour",
        travel_date=travel_date,
        status=QuotationStatus.SENT,
        subtotal=Decimal("30000.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("30000.00"),
    )
    db.add(quotation)
    db.commit()

    booking = QuotationService(db).accept_quotation(
        quotation.id,
        customer,
        travellers=[
            {"full_name": "Quote Guest One"},
            {"full_name": "Quote Guest Two"},
            {"full_name": "Quote Guest Three"},
        ],
    )
    db.refresh(departure)

    assert booking.departure_id == departure.id
    assert booking.departure_seats_reserved == 3
    assert departure.available_seats == 2


def test_public_and_customer_rankings_use_latest_balances_without_private_data(db):
    customer = make_account(db, role=AccountRole.CUSTOMER, code="C-POINTS-4", name="Private Customer Name")
    customer.email = "private.customer@example.test"
    customer.mobile = "+15555550123"
    customer.points_balance = Decimal("3.7500")
    other = make_account(db, role=AccountRole.CUSTOMER, code="C-POINTS-5", name="Another Private Name")
    other.points_balance = Decimal("1.0000")
    booking_with_ledger_payment = make_booking(
        db, customer, tour_type=TourType.DOMESTIC, amount=Decimal("200.00")
    )
    booking_with_ledger_payment.paid_amount = Decimal("100.00")
    booking_with_ledger_payment.due_amount = Decimal("100.00")
    booking_without_ledger_payment = make_booking(
        db, customer, tour_type=TourType.DOMESTIC, amount=Decimal("100.00")
    )
    booking_without_ledger_payment.paid_amount = Decimal("50.00")
    booking_without_ledger_payment.due_amount = Decimal("50.00")
    for index in range(11):
        db.add(Account(
            account_code=f"C-RANK-{index:02d}",
            name=f"Ranking Customer {index}",
            role=AccountRole.CUSTOMER,
            is_active=True,
            points_balance=Decimal("5.0000"),
        ))
    admin = make_account(db, role=AccountRole.ADMIN, code="A-POINTS-3", name="Admin Three")
    admin.email = "admin.points@example.test"
    admin.mobile = "+15555550987"
    admin.profile_pic = "https://images.example.test/admin.jpg"
    wallet = FinancialAccount(
        account_code=f"WALLET-{customer.id.hex[:12]}",
        name="Ranking Customer Wallet",
        account_type=FinancialAccountType.LIABILITY,
        owner_type=FinancialAccountOwnerType.CUSTOMER,
        owner_id=customer.id,
    )
    expense_account = FinancialAccount(
        account_code="EXP-RANKING-01",
        name="Ranking Wallet Expense",
        account_type=FinancialAccountType.EXPENSE,
        owner_type=FinancialAccountOwnerType.SYSTEM,
    )
    receivable_account = FinancialAccount(
        account_code="REC-RANKING-01",
        name="Ranking Customer Receivable",
        account_type=FinancialAccountType.ASSET,
        owner_type=FinancialAccountOwnerType.SYSTEM,
    )
    db.add_all([wallet, expense_account, receivable_account])
    db.flush()
    booking_payment = FinancialTransaction(
        transaction_code="FT-RANKING-BOOKING-PAYMENT",
        transaction_type=FinancialTransactionType.INCOME,
        status=FinancialTransactionStatus.COMPLETED,
        customer_id=customer.id,
        booking_id=booking_with_ledger_payment.id,
        amount=Decimal("100.00"),
        currency="INR",
        category=FinancialTransactionCategory.BOOKING_PAYMENT,
    )
    wallet_debit = FinancialTransaction(
        transaction_code="FT-RANKING-WALLET-DEBIT",
        transaction_type=FinancialTransactionType.EXPENSE,
        status=FinancialTransactionStatus.COMPLETED,
        customer_id=customer.id,
        amount=Decimal("30.00"),
        currency="INR",
        category=FinancialTransactionCategory.WALLET_DEBIT,
    )
    wallet_refund = FinancialTransaction(
        transaction_code="FT-RANKING-WALLET-REFUND",
        transaction_type=FinancialTransactionType.EXPENSE,
        status=FinancialTransactionStatus.COMPLETED,
        customer_id=customer.id,
        booking_id=booking_without_ledger_payment.id,
        amount=Decimal("10.00"),
        currency="INR",
        category=FinancialTransactionCategory.BOOKING_REFUND,
    )
    db.add_all([booking_payment, wallet_debit, wallet_refund])
    db.flush()
    db.add_all([
        FinancialTransactionEntry(
            transaction_id=wallet_debit.id,
            account_id=wallet.id,
            debit=Decimal("30.00"),
            credit=Decimal("0.00"),
        ),
        FinancialTransactionEntry(
            transaction_id=wallet_debit.id,
            account_id=expense_account.id,
            debit=Decimal("0.00"),
            credit=Decimal("30.00"),
        ),
        FinancialTransactionEntry(
            transaction_id=wallet_refund.id,
            account_id=receivable_account.id,
            debit=Decimal("10.00"),
            credit=Decimal("0.00"),
        ),
        FinancialTransactionEntry(
            transaction_id=wallet_refund.id,
            account_id=wallet.id,
            debit=Decimal("0.00"),
            credit=Decimal("10.00"),
        ),
    ])
    db.add(TourPointTransaction(
        account_id=customer.id,
        transaction_type=PointTransactionType.MANUAL_ADJUSTMENT,
        points=Decimal("3.7500"),
        balance_before=Decimal("0.0000"),
        balance_after=Decimal("3.7500"),
        reason="Test ranking history",
    ))
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(
        subject=customer.id,
        role=AccountRole.CUSTOMER.value,
        actor_type=AccountRole.CUSTOMER.value,
        email=customer.email,
        mobile=customer.mobile,
    )
    admin_token = create_access_token(
        subject=admin.id,
        role=AccountRole.ADMIN.value,
        actor_type=AccountRole.ADMIN.value,
        email=admin.email,
        mobile=admin.mobile,
    )
    try:
        with TestClient(app) as client:
            public_response = client.get("/api/v1/public/ranking")
            public_page_two_response = client.get("/api/v1/public/ranking?page=2")
            customer_response = client.get(
                "/api/v1/account/points",
                headers={"Authorization": f"Bearer {token}"},
            )
            rank_position_response = client.get(
                "/api/v1/account/points/rank-position",
                headers={"Authorization": f"Bearer {token}"},
            )
            config_update = client.put(
                "/api/v1/admin/points/config/DOMESTIC",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"amount_per_point": "7500.00"},
            )
            config_history_response = client.get(
                "/api/v1/admin/points/config/history?tour_type=DOMESTIC",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            config_response = client.get(
                "/api/v1/admin/points/config",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            transaction_response = client.get(
                "/api/v1/admin/points/transactions?search=Private%20Customer%20Name",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            ranking_response = client.get(
                "/api/v1/admin/points/rankings",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            public_openapi_response = client.get("/openapi/public.json")
            enduser_openapi_response = client.get("/openapi/enduser.json")
            admin_openapi_response = client.get("/openapi/admin.json")
    finally:
        app.dependency_overrides.clear()

    assert public_response.status_code == 200
    public_data = public_response.json()["data"]
    assert len(public_data) == 10
    assert public_response.json()["pagination"]["total_pages"] == 2
    page_two_data = public_page_two_response.json()["data"]
    customer_rank_row = next(row for row in page_two_data if row["customer_name"] == "Private Customer Name")
    assert customer_rank_row == {
        "rank": 12,
        "customer_name": "Private Customer Name",
        "customer_profile_picture": None,
        "customer_joined_at": customer.created_at.isoformat(),
        "point_balance": "3.7500",
    }
    assert "account_id" not in public_response.text
    assert "email" not in public_response.text

    assert customer_response.status_code == 200
    customer_data = customer_response.json()["data"]
    assert customer_data["rank"] == 12
    assert customer_data["points_balance"] == "3.7500"
    assert "around" not in customer_data
    assert customer_data["transactions"][0]["points"] == "3.7500"
    assert customer_data["transaction_pagination"]["total_items"] == 1
    assert rank_position_response.status_code == 200
    assert rank_position_response.json()["data"] == {
        "rank": 12,
        "page_number": 2,
        "page_size": 10,
        "point_balance": "3.7500",
    }
    assert config_update.status_code == 200
    assert config_history_response.status_code == 200
    changed_history = next(
        item
        for item in config_history_response.json()["data"]
        if item["changed_by_account_id"] == str(admin.id)
    )
    assert changed_history["changed_by_account_name"] == admin.name
    assert changed_history["changed_by_account_email"] == admin.email
    assert changed_history["changed_by_account_mobile"] == admin.mobile
    assert changed_history["changed_by_account_profile_pic"] == admin.profile_pic
    assert config_response.status_code == 200
    domestic_config = next(
        row for row in config_response.json()["data"] if row["tour_type"] == "DOMESTIC"
    )
    assert domestic_config["amount_per_point"] == "7500.00"
    assert transaction_response.status_code == 200
    transaction_customer = transaction_response.json()["data"][0]
    assert transaction_customer["customer_id"] == str(customer.id)
    assert transaction_customer["customer_code"] == customer.account_code
    assert transaction_customer["customer_name"] == customer.name
    assert transaction_customer["customer_email"] == customer.email
    assert transaction_customer["customer_mobile"] == customer.mobile
    assert transaction_customer["customer_profile_pic"] is None
    assert ranking_response.status_code == 200
    ranking_customer = next(
        row for row in ranking_response.json()["data"] if row["customer_id"] == str(customer.id)
    )
    assert ranking_customer == {
        "rank": ranking_customer["rank"],
        "customer_id": str(customer.id),
        "customer_code": customer.account_code,
        "customer_name": customer.name,
        "customer_profile_picture": None,
        "points": "3.7500",
        "customer_joined_at": customer.created_at.isoformat(),
        "money_spends": "170.00",
    }
    assert ranking_response.json()["pagination"] == {
        "current_page": 1,
        "page_size": 20,
        "total_items": 13,
        "total_pages": 1,
        "has_next": False,
        "has_previous": False,
    }

    assert public_openapi_response.status_code == 200
    openapi = public_openapi_response.json()
    ranking_operation = openapi["paths"]["/api/v1/public/ranking"]["get"]
    assert ranking_operation["summary"] == "List public customer point rankings"
    response_ref = ranking_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    response_schema_name = response_ref.rsplit("/", maxsplit=1)[-1]
    response_schema = openapi["components"]["schemas"][response_schema_name]
    item_ref = response_schema["properties"]["data"]["items"]["$ref"]
    item_schema_name = item_ref.rsplit("/", maxsplit=1)[-1]
    item_properties = openapi["components"]["schemas"][item_schema_name]["properties"]
    assert set(item_properties) == {
        "rank",
        "customer_name",
        "customer_profile_picture",
        "customer_joined_at",
        "point_balance",
    }
    assert "422" in ranking_operation["responses"]
    page_size_parameter = next(
        parameter for parameter in ranking_operation["parameters"] if parameter["name"] == "page_size"
    )
    assert page_size_parameter["schema"]["default"] == 10
    assert enduser_openapi_response.status_code == 200
    enduser_openapi = enduser_openapi_response.json()
    assert "/api/v1/account/points/rank-position" in enduser_openapi["paths"]
    customer_points_schema = enduser_openapi["components"]["schemas"]["CustomerPointsResponse"]
    assert set(customer_points_schema["properties"]) == {
        "points_balance",
        "rank",
        "transactions",
        "transaction_pagination",
    }
    assert admin_openapi_response.status_code == 200
    admin_openapi = admin_openapi_response.json()
    admin_paths = admin_openapi["paths"]
    assert admin_paths["/api/v1/admin/points/config"]["get"]["summary"] == (
        "Get domestic and international point rates"
    )
    update_operation = admin_paths["/api/v1/admin/points/config/{tour_type}"]["put"]
    update_body_ref = update_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    update_body_name = update_body_ref.rsplit("/", maxsplit=1)[-1]
    update_body_fields = admin_schemas_for_request = admin_openapi["components"]["schemas"][update_body_name]["properties"]
    assert "amount_per_point" in update_body_fields
    assert "required to earn one point" in update_body_fields["amount_per_point"]["description"]
    assert admin_paths["/api/v1/admin/points/transactions"]["get"]["summary"] == (
        "Search and filter point transactions"
    )
    assert {"401", "403", "422"}.issubset(
        admin_paths["/api/v1/admin/points/transactions"]["get"]["responses"]
    )
    admin_schemas = admin_openapi["components"]["schemas"]
    assert admin_schemas["PaginationMeta"]["example"] == {
        "current_page": 1,
        "page_size": 20,
        "total_items": 42,
        "total_pages": 3,
        "has_next": True,
        "has_previous": False,
    }
    assert "amount_per_point" in admin_schemas["TourPointConfigurationResponse"]["properties"]
    assert {
        "changed_by_account_profile_pic",
        "changed_by_account_name",
        "changed_by_account_email",
        "changed_by_account_mobile",
    }.issubset(admin_schemas["TourPointConfigurationHistoryResponse"]["properties"])
    assert {
        "customer_id",
        "customer_code",
        "customer_name",
        "customer_email",
        "customer_mobile",
        "customer_profile_pic",
        "booking_code",
        "points",
        "balance_after",
    }.issubset(
        admin_schemas["AdminTourPointTransactionResponse"]["properties"]
    )
    assert {"success", "message", "error"}.issubset(admin_schemas["ErrorResponse"]["properties"])
