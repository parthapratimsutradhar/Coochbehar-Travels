import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.api.v1.admin.quotations import get_quotation, list_quotations
from app.core.enums import AccountRole, BookingSource, EnquiryChannel, EnquiryStatus, EnquiryType, PaymentMethod, QuotationStatus
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.account import Account
from app.models.destination import Destination
from app.models.enquiry import Enquiry
from app.models.quotation import Quotation
from app.schemas.booking import OfflineBookingCreate
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
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


def test_offline_booking_service_accepts_actual_schema_contract(db_session, test_customer, superadmin_user):
    payload = OfflineBookingCreate(
        customer_id=test_customer.id,
        travel_date=date(2026, 10, 15),
        adult_count=2,
        child_count=1,
        senior_count=0,
        total_selling_price=25000,
        advance_received=5000,
        payment_mode=PaymentMethod.CASH,
        source=BookingSource.OFFLINE,
        special_notes="Walk-in booking",
        travellers=[
            {
                "full_name": "Jane Traveler",
                "traveler_type": "ADULT",
                "gender": "FEMALE",
                "mobile": "+919876543210",
                "email": "jane@example.com",
                "is_primary": True,
            }
        ],
        items=[
            {
                "item_type": "other",
                "name": "Tour package",
                "quantity": 1,
                "unit_price": 25000,
                "total_price": 25000,
            }
        ],
    )

    booking = BookingService(db_session).create_offline_booking(payload, superadmin_user)

    assert booking.customer_id == test_customer.id
    assert booking.total_amount == 25000
    assert booking.paid_amount == 5000
    assert booking.due_amount == 20000
    assert booking.notes == "Walk-in booking"
    assert booking.source == BookingSource.OFFLINE
    assert booking.travellers[0].full_name == "Jane Traveler"


def test_offline_booking_service_uses_package_id_schema_contract(db_session, test_customer, superadmin_user):
    package_id = uuid.uuid4()
    payload = OfflineBookingCreate(
        customer_id=test_customer.id,
        package_id=package_id,
        travel_date=date(2026, 10, 15),
        total_selling_price=25000,
        advance_received=5000,
        payment_mode=PaymentMethod.CASH,
        source=BookingSource.OFFLINE,
        travellers=[
            {
                "full_name": "Tour Guest",
                "mobile": "+919876543211",
                "email": "guest@example.com",
                "is_primary": True,
            }
        ],
    )

    booking = BookingService(db_session).create_offline_booking(payload, superadmin_user)

    assert booking.package_id == package_id


def test_offline_booking_service_uses_tour_offer_id_schema_contract(db_session, test_customer, superadmin_user):
    offer_id = uuid.uuid4()
    payload = OfflineBookingCreate(
        customer_id=test_customer.id,
        tour_offer_id=offer_id,
        travel_date=date(2026, 10, 15),
        total_selling_price=25000,
        advance_received=5000,
        payment_mode=PaymentMethod.CASH,
        source=BookingSource.OFFLINE,
        travellers=[
            {
                "full_name": "Offer Traveler",
                "mobile": "+919876543212",
                "email": "offer@example.com",
                "is_primary": True,
            }
        ],
    )

    booking = BookingService(db_session).create_offline_booking(payload, superadmin_user)

    assert booking.offer_id == offer_id


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
    assert resp.json()["success"] is True
    assert resp.json()["message"] == "Destination created successfully"
    assert "data" not in resp.json()

    # Find the created destination id from list/search response.
    list_resp = client.get(
        "/api/v1/admin/destinations/",
        headers=superadmin_auth_header,
        params={"search": "darjeeling-hills"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert len(items) >= 1
    dest_id = next(item["id"] for item in items if item["slug"] == "darjeeling-hills")

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
    assert up_resp.json()["success"] is True
    assert up_resp.json()["message"] == "Destination updated successfully"
    assert "data" not in up_resp.json()

    # Soft delete
    del_resp = client.delete(f"/api/v1/admin/destinations/{dest_id}", headers=superadmin_auth_header)
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True
    assert del_resp.json()["message"] == "Destination deleted successfully"


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


def test_admin_quotation_list_response_contract():
    with patch("app.api.v1.admin.quotations.QuotationService") as mock_service:
        item = MagicMock()
        item.id = uuid.uuid4()
        item.quotation_code = "QT-1001-V1"
        item.tour_name = "Bengal Heritage Tour"
        item.travel_date = datetime(2026, 9, 25, 9, 2, 39, 625000, tzinfo=timezone.utc)
        item.return_date = datetime(2026, 9, 30, 9, 2, 39, 625000, tzinfo=timezone.utc)
        item.total_amount = 1250.00
        item.valid_until = datetime(2026, 9, 27, 9, 2, 39, 625000, tzinfo=timezone.utc)
        item.version = 1
        item.status = "DRAFT"

        mock_service.return_value.list_all_quotations.return_value = {
            "items": [item],
            "page": 1,
            "page_size": 20,
            "total_items": 1,
            "total_pages": 1,
        }

        response = list_quotations(
            page=1,
            page_size=20,
            status_filter=None,
            search=None,
            db=MagicMock(),
            current_user=MagicMock(),
        )

        assert response.success is True
        assert response.message == "Items fetched successfully"
        assert response.pagination.current_page == 1
        assert response.pagination.page_size == 20
        assert response.pagination.total_items == 1
        assert response.pagination.total_pages == 1
        assert response.data[0].model_dump().keys() == {
            "tour_name",
            "travel_date",
            "return_date",
            "total_amount",
            "valid_until",
            "id",
            "quotation_code",
            "version",
            "status",
        }


def test_admin_quotation_detail_response_contract():
    item = SimpleNamespace()
    item.id = uuid.uuid4()
    item.quotation_code = "QT-1001-V1"
    item.customer_id = uuid.uuid4()
    item.enquiry_id = uuid.uuid4()
    item.package_id = uuid.uuid4()
    item.variant_id = uuid.uuid4()
    item.destination_id = uuid.uuid4()
    item.created_by_account_id = uuid.uuid4()
    item.tour_name = "Andaman Escape"
    item.travel_date = datetime(2026, 9, 25, 9, 34, 51, 979000, tzinfo=timezone.utc)
    item.return_date = datetime(2026, 9, 30, 9, 34, 51, 979000, tzinfo=timezone.utc)
    item.subtotal = 1000.00
    item.discount_amount = 50.00
    item.tax_amount = 75.00
    item.total_amount = 1025.00
    item.valid_until = datetime(2026, 9, 27, 9, 34, 51, 979000, tzinfo=timezone.utc)
    item.terms_and_conditions = "Terms"
    item.important_notes = "Notes"
    item.inclusion = "Inclusion"
    item.exclusion = "Exclusion"
    item.version = 1
    item.status = "DRAFT"
    item.created_by = SimpleNamespace(
        id=item.created_by_account_id,
        name="Support Admin",
        email="support@example.com",
        profile_pic="https://img.example.com/admin.png",
    )
    item.customer = SimpleNamespace(
        id=item.customer_id,
        name="Alice Customer",
        mobile="9876543210",
        email="alice@example.com",
        profile_pic="https://img.example.com/customer.png",
    )
    item.package = SimpleNamespace(
        id=item.package_id,
        title="Beach Delight",
        description="Enjoy the coast",
    )
    item.variant = SimpleNamespace(
        id=item.variant_id,
        name="Classic Summer",
        season_name="Summer",
        banner={"image": "https://img.example.com/banner.jpg", "video": "https://video.example.com/banner.mp4"},
    )
    item.destination = SimpleNamespace(id=item.destination_id, name="Andaman")
    item.created_at = datetime(2026, 9, 25, 9, 34, 51, 979000, tzinfo=timezone.utc)
    item.updated_at = datetime(2026, 9, 25, 9, 34, 51, 979000, tzinfo=timezone.utc)
    item.sent_at = None
    item.accepted_at = None
    item.rejected_at = None
    item.rejected_reason = None
    item.items = []
    item.hotels = []
    item.vehicles = []
    item.itinerary = []

    with patch("app.api.v1.admin.quotations.QuotationService") as mock_service:
        mock_service.return_value.get_quotation.return_value = item

        response = get_quotation(
            quotation_id=item.id,
            db=MagicMock(),
            current_user=MagicMock(),
        )

        assert response.success is True
        assert response.data.customer.name == "Alice Customer"
        assert response.data.package.name == "Beach Delight"
        assert response.data.variant.name == "Classic Summer"
        assert response.data.destination.name == "Andaman"
        assert response.data.created_by.name == "Support Admin"
        assert response.data.quotation_code == "QT-1001-V1"
        assert response.data.status == "DRAFT"


def test_quotation_and_booking_pipeline(client, superadmin_auth_header, test_customer, db_session):
    enquiry = Enquiry(
        enquiry_code="ENQ-QUOT-1001",
        customer_id=test_customer.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WHATSAPP,
        status=EnquiryStatus.NEW,
        enquirer_name="John Traveler",
        enquirer_phone="+919876543210",
        enquirer_email="john@example.com",
    )
    db_session.add(enquiry)
    db_session.commit()
    db_session.refresh(enquiry)

    # 1. Create Quotation
    q_resp = client.post(
        "/api/v1/admin/quotations/",
        headers=superadmin_auth_header,
        json={
            "customer_id": str(test_customer.id),
            "enquiry_id": str(enquiry.id),
            "tour_name": "Sikkim 5N/6D Tour",
            "subtotal": 50000.0,
            "discount_amount": 5000.0,
            "tax_amount": 2250.0,
            "total_amount": 47250.0,
            "items": [
                {
                    "item_type": "other",
                    "name": "Gangtok Grand Hotel",
                    "quantity": 3,
                    "unit_price": 6000.0,
                    "total_price": 18000.0,
                },
                {
                    "item_type": "transfer",
                    "name": "Innova Crysta 5 Days",
                    "quantity": 1,
                    "unit_price": 20000.0,
                    "total_price": 20000.0,
                },
            ],
        },
    )
    assert q_resp.status_code == 201, q_resp.text
    quotation = db_session.query(Quotation).order_by(Quotation.created_at.desc()).first()
    quotation_id = quotation.id
    assert float(quotation.total_amount) == 47250.0

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


def test_admin_quotation_send_marks_status_sent(client, superadmin_auth_header, test_customer, db_session, monkeypatch):
    enquiry = Enquiry(
        enquiry_code="ENQ-1002",
        customer_id=test_customer.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WHATSAPP,
        status=EnquiryStatus.NEW,
        enquirer_name="Maria Traveler",
        enquirer_phone="+919876543211",
        enquirer_email="maria@example.com",
    )
    db_session.add(enquiry)
    db_session.commit()
    db_session.refresh(enquiry)

    create_resp = client.post(
        "/api/v1/admin/quotations/",
        headers=superadmin_auth_header,
        json={
            "customer_id": str(test_customer.id),
            "enquiry_id": str(enquiry.id),
            "tour_name": "Goa Escape",
            "subtotal": 18000.0,
            "discount_amount": 500.0,
            "tax_amount": 700.0,
            "total_amount": 18200.0,
            "items": [
                {
                    "item_type": "other",
                    "name": "Beach Resort Stay",
                    "quantity": 2,
                    "unit_price": 7000.0,
                    "total_price": 14000.0,
                }
            ],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    quotation = db_session.query(Quotation).order_by(Quotation.created_at.desc()).first()

    async def fake_email_quotation(self, quotation_id, recipient_email):
        return "https://example.com/quotation.pdf"

    monkeypatch.setattr("app.services.quotation_service.QuotationService.email_quotation", fake_email_quotation)

    send_resp = client.post(
        f"/api/v1/admin/quotations/{quotation.id}/send",
        headers=superadmin_auth_header,
        json={"recipient_email": "customer@example.com"},
    )
    assert send_resp.status_code == 200, send_resp.text
    db_session.refresh(quotation)
    assert quotation.status == QuotationStatus.SENT


def test_admin_quotation_update_and_status_flow(client, superadmin_auth_header, test_customer, db_session):
    enquiry = Enquiry(
        enquiry_code="ENQ-1001",
        customer_id=test_customer.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WHATSAPP,
        status=EnquiryStatus.NEW,
        enquirer_name="John Traveler",
        enquirer_phone="+919876543210",
        enquirer_email="john@example.com",
    )
    db_session.add(enquiry)
    db_session.commit()
    db_session.refresh(enquiry)

    create_resp = client.post(
        "/api/v1/admin/quotations/",
        headers=superadmin_auth_header,
        json={
            "customer_id": str(test_customer.id),
            "enquiry_id": str(enquiry.id),
            "tour_name": "Kerala Wellness Tour",
            "subtotal": 25000.0,
            "discount_amount": 1000.0,
            "tax_amount": 1200.0,
            "total_amount": 25200.0,
            "items": [
                {
                    "item_type": "other",
                    "name": "Tea Valley Resort",
                    "quantity": 2,
                    "unit_price": 8000.0,
                    "total_price": 16000.0,
                }
            ],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    quotation = db_session.query(Quotation).order_by(Quotation.created_at.desc()).first()
    quotation_id = quotation.id

    update_resp = client.patch(
        f"/api/v1/admin/quotations/{quotation_id}",
        headers=superadmin_auth_header,
        json={"tour_name": "Kerala Wellness Deluxe Tour", "total_amount": 26000.0},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["message"] == "User updated successfully." or update_resp.json()["message"] == "Quotation updated successfully."

    status_resp = client.patch(
        f"/api/v1/admin/quotations/{quotation_id}/status",
        headers=superadmin_auth_header,
        json={"status": "SENT"},
    )
    assert status_resp.status_code == 200, status_resp.text
    assert status_resp.json()["message"] in {"User updated successfully.", "Quotation updated successfully."}

    locked_update = client.patch(
        f"/api/v1/admin/quotations/{quotation_id}",
        headers=superadmin_auth_header,
        json={"tour_name": "This update should be blocked"},
    )
    assert locked_update.status_code == 409, locked_update.text

