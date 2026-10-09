import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_admin, get_current_customer
from app.core.enums import AccountRole, BookingSource, BookingStatus, DocumentType, TourType
from app.db.database import get_db
from app.main import fastapi_app as app
from app.models.account import Account
from app.models.base import Base
from app.models.booking import Booking
from app.models.document import Document
from app.services import customer_document_service as customer_document_service_module
from app.services import cdn_service
from app.services.customer_service import CustomerService

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def create_account(db, role=AccountRole.CUSTOMER, email="user@example.com"):
    uid = uuid.uuid4()
    account = Account(
        id=uid,
        account_code=f"AC-{str(uid)[:8]}",
        email=email,
        role=role,
        is_active=True,
        name=f"User {role.value}",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def create_document(
    db,
    customer_id,
    uploaded_by_id,
    file_name="passport.pdf",
    file_url="mock://storage/file.pdf",
    booking_id=None,
    document_type=DocumentType.ID_PROOF,
):
    doc = Document(
        id=uuid.uuid4(),
        customer_id=customer_id,
        uploaded_by_account_id=uploaded_by_id,
        booking_id=booking_id,
        document_type=document_type,
        title="Passport Copy",
        file_name=file_name,
        file_url=file_url,
        mime_type="application/pdf",
        file_size=1024,
        is_active=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def test_customer_list_and_download_returns_private_blob(
    client, db_session, tmp_path, monkeypatch
):
    customer = create_account(db_session, AccountRole.CUSTOMER, "cust3@example.com")
    private_folder = tmp_path / "private" / "customer-documents"
    private_folder.mkdir(parents=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    (private_folder / filename).write_bytes(b"private document content")
    monkeypatch.setattr(cdn_service, "CDN_ROOT", tmp_path)
    doc = create_document(
        db_session,
        customer.id,
        customer.id,
        file_name="passport.pdf",
        file_url=f"private/customer-documents/{filename}",
    )

    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        # 1. Listings expose document metadata without file details.
        list_res = client.get("/api/v1/documents")
        assert list_res.status_code == 200
        doc_item = list_res.json()["data"][0]
        assert doc_item["id"] == str(doc.id)
        assert not {"file_url", "file_name", "mime_type", "file_size"} & doc_item.keys()

        # 2. The customer endpoint streams the file with private cache headers.
        dl_res = client.get(f"/api/v1/documents/{doc.id}/download")
        assert dl_res.status_code == 200
        assert dl_res.content == b"private document content"
        assert "attachment" in dl_res.headers["content-disposition"]
        assert "passport.pdf" in dl_res.headers["content-disposition"]
        assert dl_res.headers["cache-control"] == "private, no-store"
    finally:
        app.dependency_overrides.pop(get_current_customer, None)


def test_customer_list_returns_requested_document_fields(client, db_session):
    owner = create_account(db_session, AccountRole.CUSTOMER, "owner@example.com")
    uploader = create_account(db_session, AccountRole.CUSTOMER, "uploader@example.com")
    doc = create_document(db_session, owner.id, uploader.id)

    app.dependency_overrides[get_current_customer] = lambda: owner
    try:
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        payload = response.json()
        assert payload["message"] == "Items fetched successfully"
        assert set(payload["data"][0]) == {
            "id",
            "document_type",
            "title",
            "description",
            "uploaded_by_account_id",
            "uploader_name",
            "uploader_profile_pic",
            "uploaded_at",
            "type",
            "can_delete",
        }
        document = payload["data"][0]
        assert document["can_delete"] is False
        assert document["type"] == "incoming"
        assert document["id"] == str(doc.id)
    finally:
        app.dependency_overrides.pop(get_current_customer, None)


def test_customer_upload_accepts_admin_style_json_payload(client, db_session, monkeypatch):
    customer = create_account(db_session, AccountRole.CUSTOMER, "upload-customer@example.com")

    async def promote_asset(file_url, target_folder):
        assert file_url == "/api/v1/public/files/temporary/0123456789abcdef0123456789abcdef.pdf"
        assert target_folder == "private/customer-documents"
        return {"url": "", "path": "private/customer-documents/0123456789abcdef0123456789abcdef.pdf"}

    monkeypatch.setattr(customer_document_service_module, "promote_cdn_asset", promote_asset)
    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        response = client.post(
            "/api/v1/documents",
            json={
                "file": "/api/v1/public/files/temporary/0123456789abcdef0123456789abcdef.pdf",
                "file_name": "id-proof.pdf",
                "document_type": "ID_PROOF",
                "title": "  Identity proof  ",
                "description": "  Uploaded document  ",
            },
        )

        assert response.status_code == 201
        assert response.json()["message"] == "Document uploaded successfully"
        document = db_session.query(Document).one()
        assert document.customer_id == customer.id
        assert document.uploaded_by_account_id == customer.id
        assert document.title == "Identity proof"
        assert document.description == "Uploaded document"
        assert document.file_url == "private/customer-documents/0123456789abcdef0123456789abcdef.pdf"
        assert document.mime_type == "application/pdf"
    finally:
        app.dependency_overrides.pop(get_current_customer, None)


def test_customer_cannot_download_document_owned_by_another_customer(
    client, db_session
):
    owner = create_account(db_session, AccountRole.CUSTOMER, "owner2@example.com")
    uploader = create_account(db_session, AccountRole.CUSTOMER, "uploader2@example.com")
    doc = create_document(db_session, owner.id, uploader.id)

    app.dependency_overrides[get_current_customer] = lambda: uploader
    try:
        response = client.get(f"/api/v1/documents/{doc.id}/download")
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 404


def test_admin_can_download_private_document_without_public_cache(
    client, db_session, tmp_path, monkeypatch
):
    customer = create_account(db_session, AccountRole.CUSTOMER, "doc-owner@example.com")
    admin = create_account(db_session, AccountRole.ADMIN, "doc-admin@example.com")
    private_folder = tmp_path / "private" / "admin-documents"
    private_folder.mkdir(parents=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    (private_folder / filename).write_bytes(b"admin-only file")
    monkeypatch.setattr(cdn_service, "CDN_ROOT", tmp_path)
    doc = create_document(
        db_session,
        customer.id,
        admin.id,
        file_url=f"private/admin-documents/{filename}",
    )

    unauthenticated = client.get(f"/api/v1/admin/documents/{doc.id}/download")
    assert unauthenticated.status_code == 401

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        response = client.get(f"/api/v1/admin/documents/{doc.id}/download")
    finally:
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 200
    assert response.content == b"admin-only file"
    assert response.headers["cache-control"] == "private, no-store"


def test_admin_document_list_and_download_returns_protected_file(
    client, db_session, tmp_path, monkeypatch
):
    customer = create_account(db_session, AccountRole.CUSTOMER, "admin-list-owner@example.com")
    admin = create_account(db_session, AccountRole.ADMIN, "admin-list-user@example.com")
    private_folder = tmp_path / "private" / "admin-documents"
    private_folder.mkdir(parents=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    (private_folder / filename).write_bytes(b"protected document content")
    monkeypatch.setattr(cdn_service, "CDN_ROOT", tmp_path)
    doc = create_document(
        db_session,
        customer.id,
        admin.id,
        file_url=f"private/admin-documents/{filename}",
    )

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        response = client.get("/api/v1/admin/documents/identity")
    finally:
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 200
    document = response.json()["data"][0]
    assert document["id"] == str(doc.id)
    assert not {"file_url", "file_name", "mime_type", "file_size"} & document.keys()

    download_url = f"/api/v1/admin/documents/{doc.id}/download"
    unauthenticated = client.get(download_url)
    assert unauthenticated.status_code == 401

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        download = client.get(download_url)
    finally:
        app.dependency_overrides.pop(get_current_admin, None)

    assert download.status_code == 200
    assert download.content == b"protected document content"


def test_admin_can_list_documents_by_booking_id(client, db_session):
    customer = create_account(db_session, AccountRole.CUSTOMER, "booking-doc-owner@example.com")
    admin = create_account(db_session, AccountRole.ADMIN, "booking-doc-admin@example.com")
    booking = Booking(
        booking_code="BK-DOC-1",
        customer_id=customer.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        status=BookingStatus.CONFIRMED,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=1000,
        discount_amount=0,
        total_amount=1000,
        paid_amount=0,
        due_amount=1000,
        created_by=admin.id,
    )
    other_booking = Booking(
        booking_code="BK-DOC-2",
        customer_id=customer.id,
        booking_type=TourType.DOMESTIC,
        source=BookingSource.WEBSITE,
        status=BookingStatus.CONFIRMED,
        adult_count=1,
        child_count=0,
        senior_count=0,
        subtotal=1000,
        discount_amount=0,
        total_amount=1000,
        paid_amount=0,
        due_amount=1000,
        created_by=admin.id,
    )
    db_session.add_all([booking, other_booking])
    db_session.commit()
    expected = create_document(
        db_session,
        customer.id,
        admin.id,
        booking_id=booking.id,
        document_type=DocumentType.TOUR_DOCUMENT,
    )
    create_document(
        db_session,
        customer.id,
        admin.id,
        booking_id=other_booking.id,
        document_type=DocumentType.TOUR_DOCUMENT,
    )

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        response = client.get(
            "/api/v1/admin/documents/booking",
            params={"booking_id": str(booking.id)},
        )
    finally:
        app.dependency_overrides.pop(get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["data"]] == [str(expected.id)]
    assert payload["data"][0]["booking_id"] == str(booking.id)


def test_customer_booking_documents_can_be_filtered_by_booking_id(client, db_session):
    customer = create_account(db_session, AccountRole.CUSTOMER, "customer-booking-docs@example.com")
    admin = create_account(db_session, AccountRole.ADMIN, "booking-docs-admin@example.com")
    bookings = [
        Booking(
            booking_code=f"BK-CUST-DOC-{number}",
            customer_id=customer.id,
            booking_type=TourType.DOMESTIC,
            source=BookingSource.WEBSITE,
            status=BookingStatus.CONFIRMED,
            adult_count=1,
            child_count=0,
            senior_count=0,
            subtotal=1000,
            discount_amount=0,
            total_amount=1000,
            paid_amount=0,
            due_amount=1000,
            created_by=admin.id,
        )
        for number in (1, 2)
    ]
    db_session.add_all(bookings)
    db_session.commit()
    documents = [
        create_document(
            db_session,
            customer.id,
            customer.id,
            booking_id=booking.id,
            document_type=DocumentType.TOUR_DOCUMENT,
        )
        for booking in bookings
    ]

    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        all_response = client.get("/api/v1/documents/booking")
        filtered_response = client.get(
            "/api/v1/documents/booking",
            params={"booking_id": str(bookings[0].id)},
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert all_response.status_code == 200
    assert {item["id"] for item in all_response.json()["data"]} == {
        str(document.id) for document in documents
    }
    assert filtered_response.status_code == 200
    assert [item["id"] for item in filtered_response.json()["data"]] == [
        str(documents[0].id)
    ]


def test_customer_documents_tab_builds_valid_payload(db_session):
    customer = create_account(db_session, AccountRole.CUSTOMER, "cust4@example.com")
    admin = create_account(db_session, AccountRole.ADMIN, "admin2@example.com")
    doc = create_document(db_session, customer.id, admin.id, file_name="visa.pdf")

    payload = CustomerService(db_session).get_customer_tab_data(
        customer_id=customer.id,
        customer=customer,
        tab="documents",
        page=1,
        page_size=10,
    )

    assert payload["tab"] == "documents"
    assert payload["items"]
    item = payload["items"][0]
    assert item["id"] == str(doc.id)
    assert item["uploaded_by_account_id"] == str(admin.id)
    assert item["type"] == "incoming"
    assert item["can_delete"] is False
    assert not {"file_url", "file_name", "mime_type", "file_size", "uploaded_by"} & item.keys()
