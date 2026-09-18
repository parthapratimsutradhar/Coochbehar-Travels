import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.core.enums import AccountRole, EnquiryChannel, EnquiryType, LeadStatus
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.services.auth_service import AuthService
from app.utils.security import create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_account(db_session, code: str, role: AccountRole, name: str) -> Account:
    account = Account(
        account_code=code,
        name=name,
        email=f"{code.lower()}@example.com",
        mobile=f"+91900000{len(code):04d}",
        role=role,
        is_active=True,
    )
    db_session.add(account)
    db_session.flush()
    return account


def auth_header(account: Account) -> dict[str, str]:
    token = create_access_token(
        subject=account.id,
        role=account.role.value,
        actor_type=account.role.value,
        email=account.email,
        mobile=account.mobile,
    )
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_assign_update_and_add_lead_activity(client, db_session):
    admin = make_account(db_session, "ADM-LEAD", AccountRole.ADMIN, "Admin")
    salesperson = make_account(db_session, "STF-LEAD", AccountRole.STAFF, "Rahul")
    enquiry = Enquiry(
        enquiry_code="ENQ-LEAD01",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()
    lead = Lead(lead_code="LEAD-API01", enquiry_id=enquiry.id, status=LeadStatus.NEW)
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    headers = auth_header(admin)
    lead_url = f"/api/v1/admin/leads/{lead.id}"

    assignment = client.put(
        f"{lead_url}/assignment",
        headers=headers,
        json={"assigned_account_id": str(salesperson.id)},
    )
    assert assignment.status_code == 200
    assert assignment.json()["message"] == "Lead updated successfully."

    status_response = client.patch(
        f"{lead_url}/status",
        headers=headers,
        json={"status": "FOLLOW_UP"},
    )
    assert status_response.status_code == 200

    activity = client.post(
        f"{lead_url}/activities",
        headers=headers,
        json={
            "channel": "PHONE",
            "activity_type": "CALL",
            "notes": "Customer interested",
        },
    )
    assert activity.status_code == 201
    assert activity.json()["message"] == "Lead activity created successfully"

    timeline = client.get(f"{lead_url}/activities", headers=headers)
    assert timeline.status_code == 200
    assert any(item["notes"] == "Customer interested" for item in timeline.json()["data"])

    db_session.refresh(lead)
    assert lead.assigned_account_id == salesperson.id
    assert lead.status == LeadStatus.FOLLOW_UP
    assert lead.last_contacted_at is not None
    assert sum(activity.notes == "Customer interested" for activity in lead.activities) == 1


def test_admin_can_unassign_lead(client, db_session):
    admin = make_account(db_session, "ADM-UNAS", AccountRole.ADMIN, "Admin")
    enquiry = Enquiry(
        enquiry_code="ENQ-UNAS01",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()
    lead = Lead(
        lead_code="LEAD-UNAS1",
        enquiry_id=enquiry.id,
        assigned_account_id=admin.id,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    db_session.commit()

    response = client.put(
        f"/api/v1/admin/leads/{lead.id}/assignment",
        headers=auth_header(admin),
        json={"assigned_account_id": None},
    )

    assert response.status_code == 200
    db_session.refresh(lead)
    assert lead.assigned_account_id is None


def test_lost_reason_is_rejected_for_non_lost_status(client, db_session):
    admin = make_account(db_session, "ADM-LOSS", AccountRole.ADMIN, "Admin")
    enquiry = Enquiry(
        enquiry_code="ENQ-LOSS01",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()
    lead = Lead(lead_code="LEAD-LOSS1", enquiry_id=enquiry.id, status=LeadStatus.NEW)
    db_session.add(lead)
    db_session.commit()

    response = client.patch(
        f"/api/v1/admin/leads/{lead.id}/status",
        headers=auth_header(admin),
        json={"status": "FOLLOW_UP", "lost_reason": "NO_RESPONSE"},
    )

    assert response.status_code == 422
    assert response.json()["message"] == "A lost reason can only be used when the lead status is LOST."


def test_admin_can_update_and_delete_lead_activity(client, db_session):
    admin = make_account(db_session, "ADM-ACT", AccountRole.ADMIN, "Admin")
    enquiry = Enquiry(
        enquiry_code="ENQ-ACTAPI",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()
    lead = Lead(lead_code="LEAD-ACTAPI", enquiry_id=enquiry.id, status=LeadStatus.NEW, lead_score=10)
    db_session.add(lead)
    db_session.commit()

    headers = auth_header(admin)
    lead_url = f"/api/v1/admin/leads/{lead.id}"
    created = client.post(
        f"{lead_url}/activities",
        headers=headers,
        json={"channel": "PHONE", "activity_type": "CALL", "notes": "Initial call"},
    )
    assert created.status_code == 201

    db_session.refresh(lead)
    activity_id = lead.activities[0].id
    score_after_create = lead.lead_score

    updated = client.patch(
        f"{lead_url}/activities/{activity_id}",
        headers=headers,
        json={"notes": "Updated call notes"},
    )
    assert updated.status_code == 200

    deleted = client.delete(f"{lead_url}/activities/{activity_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Lead deleted successfully."

    db_session.refresh(lead)
    assert all(activity.id != activity_id for activity in lead.activities)
    assert lead.lead_score == 10
    assert score_after_create > 10
