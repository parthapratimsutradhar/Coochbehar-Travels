import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_actor, get_current_customer
from app.core.enums import AccountRole, DocumentType
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.document import Document
from app.services import customer_document_service as customer_document_service_module
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


def create_document(db, customer_id, uploaded_by_id, file_name="passport.pdf", file_url="mock://storage/file.pdf"):
    doc = Document(
        id=uuid.uuid4(),
        customer_id=customer_id,
        uploaded_by_account_id=uploaded_by_id,
        document_type=DocumentType.ID_PROOF,
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


def test_proxy_requires_authentication(client):
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/documents/{random_id}/file")
    assert response.status_code == 401


def test_proxy_customer_cannot_access_other_customer_document(client, db_session):
    customer_a = create_account(db_session, AccountRole.CUSTOMER, "a@example.com")
    customer_b = create_account(db_session, AccountRole.CUSTOMER, "b@example.com")
    doc_a = create_document(db_session, customer_a.id, customer_a.id)

    # Act as customer_b
    app.dependency_overrides[get_current_actor] = lambda: (customer_b, customer_b.role)
    try:
        response = client.get(f"/api/v1/documents/{doc_a.id}/file")
        assert response.status_code == 403
        assert "You do not have permission" in response.json()["message"]
    finally:
        app.dependency_overrides.pop(get_current_actor, None)


def test_proxy_customer_can_access_own_document(client, db_session):
    customer = create_account(db_session, AccountRole.CUSTOMER, "cust@example.com")
    doc = create_document(db_session, customer.id, customer.id, file_name="my_passport.pdf")

    app.dependency_overrides[get_current_actor] = lambda: (customer, customer.role)
    try:
        response = client.get(f"/api/v1/documents/{doc.id}/file")
        assert response.status_code == 200
        assert "inline" in response.headers["content-disposition"]
        assert "my_passport.pdf" in response.headers["content-disposition"]
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"mock document content"
    finally:
        app.dependency_overrides.pop(get_current_actor, None)


def test_proxy_admin_can_access_any_customer_document(client, db_session):
    admin = create_account(db_session, AccountRole.ADMIN, "admin@example.com")
    customer = create_account(db_session, AccountRole.CUSTOMER, "cust2@example.com")
    doc = create_document(db_session, customer.id, customer.id, file_name="visa.pdf")

    app.dependency_overrides[get_current_actor] = lambda: (admin, admin.role)
    try:
        response = client.get(f"/api/v1/documents/{doc.id}/file?download=true")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "visa.pdf" in response.headers["content-disposition"]
    finally:
        app.dependency_overrides.pop(get_current_actor, None)


def test_customer_list_and_download_return_proxy_urls(client, db_session):
    customer = create_account(db_session, AccountRole.CUSTOMER, "cust3@example.com")
    doc = create_document(db_session, customer.id, customer.id)

    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        # 1. Test listing returns proxy URL
        list_res = client.get("/api/v1/documents")
        assert list_res.status_code == 200
        doc_item = list_res.json()["data"][0]
        assert doc_item["file_url"] == f"/api/v1/documents/{doc.id}/file"

        # 2. Test download endpoint returns proxy URL
        dl_res = client.get(f"/api/v1/documents/{doc.id}/download")
        assert dl_res.status_code == 200
        assert dl_res.json()["data"]["download_url"] == f"/api/v1/documents/{doc.id}/file?download=true"
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
            "customer_id",
            "customer_name",
            "customer_profile_pic",
            "uploaded_by_account_id",
            "uploader_name",
            "uploader_profile_pic",
            "uploaded_at",
            "file_url",
            "file_name",
            "mime_type",
            "file_size",
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
        assert file_url == "https://storage.example/temporary-uploads/id-proof.pdf"
        assert target_folder == "customer-documents"
        return {"url": "https://storage.example/customer-documents/id-proof.pdf"}

    monkeypatch.setattr(customer_document_service_module, "promote_cloudinary_asset", promote_asset)
    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        response = client.post(
            "/api/v1/documents",
            json={
                "file": "https://storage.example/temporary-uploads/id-proof.pdf",
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
        assert document.file_url == "https://storage.example/customer-documents/id-proof.pdf"
        assert document.mime_type == "application/pdf"
    finally:
        app.dependency_overrides.pop(get_current_customer, None)


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
    assert item["uploaded_by"] == "ADMIN"
    assert item["type"] == "incoming"
