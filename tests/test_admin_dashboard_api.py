from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.core.enums import (
    AccountRole,
    BookingSource,
    BookingStatus,
    EnquiryChannel,
    EnquiryStatus,
    EnquiryType,
    HotelCategory,
    TourType,
    VehicleType,
)
from app.db.database import get_db
from app.main import fastapi_app as app
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.destination import Destination
from app.models.enquiry import Enquiry
from app.models.hotel import Hotel
from app.models.tour_package import TourPackage
from app.models.vehicle import Vehicle
from app.utils.security import create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def admin_user(db_session):
    user = Account(
        account_code="ADM-001",
        name="Admin User",
        email="admin@example.com",
        mobile="+919000000001",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(account: Account) -> dict[str, str]:
    token = create_access_token(
        subject=account.id,
        role=account.role.value,
        actor_type=account.role.value,
        email=account.email,
        mobile=account.mobile,
    )
    return {"Authorization": f"Bearer {token}"}


def test_admin_dashboard_route_returns_database_derived_dashboard_payload(client, admin_user):
    response = client.get("/api/v1/admin/dashboard", headers=auth_header(admin_user))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Dashboard data fetched successfully"
    assert payload["data"]["summary"]["today_bookings"] >= 0
    assert payload["data"]["summary"]["today_revenue"] >= 0
    assert payload["data"]["platform_metrics"]["hotels_listed"] >= 0
    assert payload["data"]["top_destinations"] is not None
    assert payload["data"]["recent_bookings"] is not None


def test_admin_dashboard_route_uses_live_database_values(client, admin_user, db_session):
    destination = Destination(
        name="Puri",
        slug="puri",
        country="India",
        image_url="https://cdn.example.com/puri.jpg",
        is_domestic=True,
        is_featured=True,
    )
    enquiry_destination = Destination(
        name="Konark",
        slug="konark",
        country="India",
        image_url="https://cdn.example.com/konark.jpg",
        is_domestic=True,
        is_featured=True,
    )
    db_session.add_all([destination, enquiry_destination])
    db_session.flush()

    customer = Account(
        account_code="CUST-001",
        name="Live Customer",
        email="customer@example.com",
        mobile="+919000000002",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    enquiry = Enquiry(
        enquiry_code="ENQ-DASH-001",
        enquiry_type=EnquiryType.CUSTOM_TOUR,
        channel=EnquiryChannel.WEBSITE,
        status=EnquiryStatus.NEW,
        destination_id=enquiry_destination.id,
        customer_id=customer.id,
    )
    package = TourPackage(
        tour_code="TP-100",
        slug="puri-beach-holiday",
        title="Puri Beach Holiday",
        destination_id=destination.id,
        type=TourType.DOMESTIC,
        is_featured=True,
    )
    hotel = Hotel(
        name="Blue Sea Hotel",
        image=[],
        destination_id=destination.id,
        category=HotelCategory.STANDARD,
    )
    vehicle = Vehicle(
        name="Tempo Traveller",
        vehicle_image=[],
        vehicle_type=VehicleType.TEMPO,
        registration_number="WB-26-AB-1234",
        capacity=12,
        price_per_day=3500,
    )

    db_session.add_all([customer, enquiry, package, hotel, vehicle])
    db_session.flush()

    booking_one = Booking(
        booking_code="BK-DATA-1",
        customer_id=customer.id,
        package_id=None,
        enquiry_id=enquiry.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        sales_account_id=admin_user.id,
        status=BookingStatus.CONFIRMED,
        adult_count=2,
        child_count=0,
        senior_count=0,
        subtotal=8000,
        discount_amount=500,
        total_amount=7500,
        paid_amount=7500,
        due_amount=0,
        created_by=admin_user.id,
    )
    booking_two = Booking(
        booking_code="BK-DATA-2",
        customer_id=customer.id,
        package_id=package.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WHATSAPP,
        sales_account_id=admin_user.id,
        status=BookingStatus.TENTATIVE,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=5000,
        discount_amount=0,
        total_amount=5000,
        paid_amount=0,
        due_amount=5000,
        created_by=admin_user.id,
    )
    db_session.add_all([booking_one, booking_two])
    db_session.commit()

    response = client.get("/api/v1/admin/dashboard", headers=auth_header(admin_user))

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["summary"]["today_bookings"] == 2
    assert payload["summary"]["today_revenue"] == 12500
    assert payload["summary"]["total_bookings"]["count"] == 2
    assert payload["summary"]["registered_users"]["count"] >= 1
    assert payload["platform_metrics"]["hotels_listed"] >= 1
    assert payload["platform_metrics"]["tour_packages"] >= 1
    assert payload["platform_metrics"]["bus_routes"] >= 1
    destinations = {item["name"]: item for item in payload["top_destinations"]}
    assert destinations["Puri"]["image_url"] == "https://cdn.example.com/puri.jpg"
    assert destinations["Konark"]["image_url"] == "https://cdn.example.com/konark.jpg"
    assert payload["recent_bookings"][0]["booking_id"] in {"BK-DATA-1", "BK-DATA-2"}


def test_dashboard_due_amount_and_outstanding_booking_filters(client, admin_user, db_session):
    customer = Account(
        account_code="CUST-DUE-001",
        name="Due Customer",
        email="due-customer@example.com",
        mobile="+919000000003",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(customer)
    db_session.flush()

    collectible_booking = Booking(
        booking_code="BK-DUE-001",
        customer_id=customer.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        sales_account_id=admin_user.id,
        status=BookingStatus.PARTIALLY_PAID,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=150,
        discount_amount=0,
        total_amount=150,
        paid_amount=Decimal("24.50"),
        due_amount=Decimal("125.50"),
        created_by=admin_user.id,
    )
    cancelled_booking = Booking(
        booking_code="BK-DUE-002",
        customer_id=customer.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        sales_account_id=admin_user.id,
        status=BookingStatus.CANCELLED,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=80,
        discount_amount=0,
        total_amount=80,
        paid_amount=0,
        due_amount=80,
        created_by=admin_user.id,
    )
    international_booking = Booking(
        booking_code="BK-DUE-003",
        customer_id=customer.id,
        booking_type=TourType.INTERNATIONAL,
        source=BookingSource.WEBSITE,
        sales_account_id=admin_user.id,
        status=BookingStatus.CONFIRMED,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=200,
        discount_amount=0,
        total_amount=200,
        paid_amount=100,
        due_amount=100,
        created_by=admin_user.id,
    )
    db_session.add_all([collectible_booking, cancelled_booking, international_booking])
    db_session.commit()
    headers = auth_header(admin_user)

    dashboard_response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    assert Decimal(dashboard_response.json()["data"]["summary"]["due_amount"]) == Decimal("225.50")

    unfiltered_response = client.get(
        "/api/v1/admin/financial/outstanding-bookings",
        headers=headers,
    )
    assert unfiltered_response.status_code == 200, unfiltered_response.text
    assert unfiltered_response.json()["pagination"]["total_items"] == 2

    domestic_response = client.get(
        "/api/v1/admin/financial/outstanding-bookings",
        params={
            "tour_type": "DOMESTIC",
            "status": "PARTIALLY_PAID",
            "min_due": "100",
            "max_due": "150",
            "search": "Due Customer",
        },
        headers=headers,
    )
    assert domestic_response.status_code == 200, domestic_response.text
    outstanding_data = domestic_response.json()
    assert outstanding_data["pagination"]["total_items"] == 1
    assert outstanding_data["data"][0]["booking_code"] == "BK-DUE-001"
    assert Decimal(outstanding_data["data"][0]["due_amount"]) == Decimal("125.50")

    international_response = client.get(
        "/api/v1/admin/financial/outstanding-bookings",
        params={"tour_type": "INTERNATIONAL"},
        headers=headers,
    )
    assert international_response.status_code == 200, international_response.text
    assert international_response.json()["pagination"]["total_items"] == 1
    assert international_response.json()["data"][0]["booking_code"] == "BK-DUE-003"

    invalid_filter_response = client.get(
        "/api/v1/admin/financial/outstanding-bookings",
        params={"min_due": "200", "max_due": "100"},
        headers=headers,
    )
    assert invalid_filter_response.status_code == 422
