import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.core.enums import AccountRole
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.account import Account
from app.models.destination import Destination
from app.services.auth_service import AuthService
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

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def superadmin_user(db_session):
    user = Account(
        account_code="SA-001",
        name="Super Admin",
        email="superadmin@example.com",
        mobile="+919999999991",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superadmin_auth_header(superadmin_user):
    token = create_access_token(
        subject=superadmin_user.id,
        role=superadmin_user.role.value,
        actor_type=superadmin_user.role.value,
        email=superadmin_user.email,
        mobile=superadmin_user.mobile,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_customer(db_session):
    customer = Account(
        account_code="CUST-001",
        name="John Traveler",
        email="john@example.com",
        mobile="+919876543210",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def test_destination_crud(client, superadmin_auth_header):
    # Create destination
    resp = client.post(
        "/api/v1/admin/destinations/",
        headers=superadmin_auth_header,
        json={
            "name": "Darjeeling Hills",
            "slug": "darjeeling-hills",
            "state": "West Bengal",
            "country": "India",
            "description": "Queen of the hills",
            "is_active": True,
        },
    )
    assert resp.status_code == 201, resp.text
    dest = resp.json()["data"]
    dest_id = dest["id"]
    assert dest["name"] == "Darjeeling Hills"

    # List destinations
    list_resp = client.get("/api/v1/admin/destinations/", headers=superadmin_auth_header)
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) >= 1

    # Public list
    pub_resp = client.get("/api/v1/public/destinations/")
    assert pub_resp.status_code == 200
    assert any(d["slug"] == "darjeeling-hills" for d in pub_resp.json()["data"])

    # Update destination
    up_resp = client.patch(
        f"/api/v1/admin/destinations/{dest_id}",
        headers=superadmin_auth_header,
        json={"name": "Darjeeling & Kalimpong"},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["data"]["name"] == "Darjeeling & Kalimpong"

    # Soft delete
    del_resp = client.delete(f"/api/v1/admin/destinations/{dest_id}", headers=superadmin_auth_header)
    assert del_resp.status_code == 200


def test_vendor_and_expenses(client, superadmin_auth_header):
    # Create Vendor
    v_resp = client.post(
        "/api/v1/admin/vendors/",
        headers=superadmin_auth_header,
        json={
            "type": "HOTEL",
            "name": "Himalayan Retreat Hotel",
            "contact": "+919800011223",
            "email": "sharma@retreat.com",
            "address": "Darjeeling",
        },
    )
    assert v_resp.status_code == 201, v_resp.text
    vendor_id = v_resp.json()["data"]["id"]

    # List vendors
    v_list = client.get("/api/v1/admin/vendors/", headers=superadmin_auth_header)
    assert v_list.status_code == 200
    assert len(v_list.json()["data"]) >= 1

    # Create Expense
    exp_resp = client.post(
        "/api/v1/admin/expenses/",
        headers=superadmin_auth_header,
        json={
            "expense_category": "OFFICE_RENT",
            "amount": 25000.0,
            "payment_method": "NET_BANKING",
            "description": "Monthly Office Rent",
        },
    )
    assert exp_resp.status_code == 201, exp_resp.text
    assert float(exp_resp.json()["data"]["amount"]) == 25000.0

    # List Expenses
    exp_list = client.get("/api/v1/admin/expenses/", headers=superadmin_auth_header)
    assert exp_list.status_code == 200
    assert len(exp_list.json()["data"]) >= 1


def test_quotation_and_booking_pipeline(client, superadmin_auth_header, test_customer):
    # 1. Create Quotation
    q_resp = client.post(
        "/api/v1/admin/quotations/",
        headers=superadmin_auth_header,
        json={
            "customer_id": str(test_customer.id),
            "tour_name": "Sikkim 5N/6D Tour",
            "adult_count": 2,
            "child_count": 1,
            "subtotal": 50000.0,
            "discount_amount": 5000.0,
            "tax_amount": 2250.0,
            "total_amount": 47250.0,
            "items": [
                {
                    "item_type": "hotel",
                    "name": "Gangtok Grand Hotel",
                    "quantity": 3,
                    "unit_price": 6000.0,
                    "total_price": 18000.0,
                },
                {
                    "item_type": "transport",
                    "name": "Innova Crysta 5 Days",
                    "quantity": 1,
                    "unit_price": 20000.0,
                    "total_price": 20000.0,
                },
            ],
        },
    )
    assert q_resp.status_code == 201, q_resp.text
    quotation = q_resp.json()["data"]
    quotation_id = quotation["id"]
    assert float(quotation["total_amount"]) == 47250.0

    # 2. Get Quotation
    get_q = client.get(f"/api/v1/admin/quotations/{quotation_id}", headers=superadmin_auth_header)
    assert get_q.status_code == 200
    assert len(get_q.json()["data"]["items"]) == 2

    # 3. Convert Quotation to Booking
    conv_resp = client.post(
        f"/api/v1/admin/quotations/{quotation_id}/convert",
        headers=superadmin_auth_header,
        json={
            "booking_type": "CUSTOM_PACKAGE",
            "notes": "Window seat preferred",
        },
    )
    assert conv_resp.status_code == 201, conv_resp.text
    booking = conv_resp.json()["data"]
    booking_id = booking["id"]
    assert booking["quotation_id"] == quotation_id

    # 4. Add Traveler to Booking
    trav_resp = client.post(
        f"/api/v1/admin/bookings/{booking_id}/travellers",
        headers=superadmin_auth_header,
        json={
            "full_name": "Alice Traveler",
            "traveler_type": "ADULT",
            "gender": "FEMALE",
            "is_primary": True,
        },
    )
    assert trav_resp.status_code == 201, trav_resp.text

    # 5. Record Payment for Booking
    pay_resp = client.post(
        f"/api/v1/admin/bookings/{booking_id}/payments",
        headers=superadmin_auth_header,
        json={
            "amount": 20000.0,
            "payment_method": "UPI",
            "transaction_type": "PAYMENT",
            "status": "SUCCESS",
            "notes": "Advance payment",
        },
    )
    assert pay_resp.status_code == 201, pay_resp.text

    # 6. Check updated Booking details
    b_get = client.get(f"/api/v1/admin/bookings/{booking_id}", headers=superadmin_auth_header)
    assert b_get.status_code == 200
    b_data = b_get.json()["data"]
    assert float(b_data["paid_amount"]) == 20000.0
    assert len(b_data["travellers"]) == 1

    # 7. Check Dashboard Analytics
    dash_resp = client.get("/api/v1/admin/analytics/dashboard", headers=superadmin_auth_header)
    assert dash_resp.status_code == 200, dash_resp.text
    dash_data = dash_resp.json()["data"]
    assert "today" in dash_data
    assert "future_business" in dash_data
    assert "pipeline" in dash_data
    assert "current_year" in dash_data
    assert "current_month" in dash_data
    assert dash_data["today"]["new_bookings"] == 1
    assert float(dash_data["today"]["revenue"]) == 47250.0

