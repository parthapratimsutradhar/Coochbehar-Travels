import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType, LeadSource, LeadStatus, UserRole
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.tour_package import TourPackage
from app.models.user import User
from app.models.visitor import Visitor
from app.models.visitor_session import VisitorSession
from app.services.lead_scoring_service import LeadScoringService
from app.services.tracking_service import TrackingService

# Enable JSONB support in SQLite in-memory test database
compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create clean database tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Yield a database session for test setup and assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── 1. Model Schema Integrity ─────────────────────────────────────────

def test_visitor_model_has_no_lead_score():
    """Ensure Visitor model does not contain lead_score column/attribute."""
    visitor_columns = [col.name for col in Visitor.__table__.columns]
    assert "lead_score" not in visitor_columns
    assert not hasattr(Visitor, "lead_score")


def test_lead_model_has_lead_score():
    """Ensure Lead model contains lead_score as single source of truth."""
    lead_columns = [col.name for col in Lead.__table__.columns]
    assert "lead_score" in lead_columns
    lead = Lead(
        lead_code="LEAD-TEST01",
        full_name="John Doe",
        lead_score=50,
        status=LeadStatus.NEW,
    )
    assert lead.lead_score == 50


# ── 2. LeadScoringService Unit Tests ──────────────────────────────────

def test_calculate_initial_score_full_enquiry(db_session):
    """Verify initial score calculation with all high-intent enquiry fields."""
    scoring = LeadScoringService(db_session)
    enquiry = {
        "travel_date": date(2026, 10, 15),
        "destination": "Sikkim & Darjeeling",
        "pax_no": 4,
        "package_id": uuid.uuid4(),
        "enquirer_phone": "+919876543210",
        "enquirer_name": "Partha Sutradhar",
        "message": "Need family package with vehicle and vegetarian meals",
    }
    # Base (20) + date (10) + dest (5) + pax (5) + pkg (10) + phone (10) + name (5) + msg (5) = 70
    score = scoring.calculate_initial_score(enquiry)
    assert score == 70


def test_calculate_initial_score_minimal_enquiry(db_session):
    """Verify initial score calculation with bare minimal enquiry."""
    scoring = LeadScoringService(db_session)
    enquiry = {
        "enquirer_name": None,
        "enquirer_phone": None,
    }
    # Base (20)
    score = scoring.calculate_initial_score(enquiry)
    assert score == 20


def test_score_boundaries_clamped(db_session):
    """Verify lead score is strictly bounded in [0, 100]."""
    scoring = LeadScoringService(db_session)
    lead = Lead(lead_code="LEAD-BOUNDS", full_name="Tester", lead_score=95)
    
    # Over-increment (> 100)
    prev, new_s, delta = scoring.apply_score_change(lead, 20)
    assert new_s == 100
    assert lead.lead_score == 100
    assert delta == 5  # actual delta applied

    # Under-decrement (< 0)
    prev, new_s, delta = scoring.apply_score_change(lead, -150)
    assert new_s == 0
    assert lead.lead_score == 0
    assert delta == -100


# ── 3. Enquiry -> Lead Creation Endpoints ─────────────────────────────

def test_visitor_submits_enquiry_creates_lead_with_initial_score(client: TestClient, db_session, monkeypatch):
    """Visitor submits enquiry -> Enquiry + Lead created with calculated initial score and Socket.IO emitted."""
    emitted_events = []

    def mock_emit_lead_created(lead):
        emitted_events.append(("lead:created", lead.lead_code, lead.lead_score))

    monkeypatch.setattr("app.api.v1.enduser.enquiries.emit_lead_created", mock_emit_lead_created)

    # Create visitor
    visitor = Visitor(visitor_code="VIS-ENQ01")
    db_session.add(visitor)
    db_session.commit()
    db_session.refresh(visitor)

    res = client.post(
        "/api/v1/enquiries",
        json={
            "visitor_id": str(visitor.id),
            "name": "Jane Explorer",
            "mobile": "+919876500000",
            "subject": "Sikkim Explorer",
            "message": "Looking for 5-day package",
            "channel": "WEBSITE",
        },
    )
    assert res.status_code == 201

    # Verify DB state
    lead = db_session.execute(select(Lead).where(Lead.visitor_id == visitor.id)).scalar_one_or_none()
    assert lead is not None
    assert lead.full_name == "Jane Explorer"
    assert lead.mobile == "+919876500000"
    # Base (20) + phone (10) + name (5) + msg (5) = 40
    assert lead.lead_score == 40
    assert lead.status == LeadStatus.NEW

    # Verify Socket.IO emit
    assert len(emitted_events) == 1
    assert emitted_events[0][0] == "lead:created"
    assert emitted_events[0][2] == 40


def test_customer_submits_custom_tour_creates_lead(client: TestClient, db_session, monkeypatch):
    """Customer submits custom tour -> Enquiry + Lead created linked to Customer."""
    emitted_events = []

    def mock_emit_lead_created(lead):
        emitted_events.append(("lead:created", lead.lead_code, lead.lead_score))

    monkeypatch.setattr("app.api.v1.enduser.enquiries.emit_lead_created", mock_emit_lead_created)

    customer = Customer(customer_code="CUS-SCORE01", name="Alice Wonderland", referral_code="REF-ALICE01")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    res = client.post(
        "/api/v1/enquiries/custom",
        json={
            "customer_id": str(customer.id),
            "name": "Alice Wonderland",
            "mobile": "+919876511111",
            "destination": "Dooars Wildlife",
            "travel_date": "2026-11-20",
            "pax_no": 6,
            "no_room": 3,
            "special_requirements": "Jeep safari included",
            "channel": "WEBSITE",
        },
    )
    assert res.status_code == 201

    lead = db_session.execute(select(Lead).where(Lead.customer_id == customer.id)).scalar_one_or_none()
    assert lead is not None
    assert lead.customer_id == customer.id
    # Base (20) + date (10) + dest (5) + pax (5) + phone (10) + name (5) + msg (5) = 60
    assert lead.lead_score == 60
    assert len(emitted_events) == 1


# ── 4. Visitor Telemetry -> Lead Score Synchronization ────────────────

def test_visitor_telemetry_updates_lead_score(client: TestClient, db_session, monkeypatch):
    """Telemetry events from identified visitor with Lead dynamically update Lead.lead_score."""
    score_events = []

    def mock_emit_lead_score_updated(lead, previous_score, new_score, delta, reason):
        score_events.append((previous_score, new_score, delta, reason))

    monkeypatch.setattr("app.services.tracking_service.emit_lead_score_updated", mock_emit_lead_score_updated)

    # 1. Setup visitor and session
    visitor = Visitor(visitor_code="VIS-DYN01")
    db_session.add(visitor)
    db_session.flush()

    session = VisitorSession(visitor_id=visitor.id)
    db_session.add(session)
    db_session.flush()

    # 2. Submit enquiry -> Lead created (score = 40)
    enquiry = Enquiry(
        enquiry_code="ENQ-DYN01",
        visitor_id=visitor.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
        enquirer_name="Telemetry User",
        enquirer_phone="+919876522222",
    )
    db_session.add(enquiry)
    db_session.flush()

    lead = Lead(
        lead_code="LEAD-DYN01",
        enquiry_id=enquiry.id,
        visitor_id=visitor.id,
        full_name="Telemetry User",
        mobile="+919876522222",
        lead_score=35,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    db_session.commit()

    # 3. Visitor checks itinerary (+4 points)
    res1 = client.post(
        "/api/v1/visitors/events",
        json={
            "visitor_id": str(visitor.id),
            "session_id": str(session.id),
            "event_name": "itinerary_view",
            "page": "/tours/sikkim-5d",
        },
    )
    assert res1.status_code == 201
    db_session.refresh(lead)
    assert lead.lead_score == 39  # 35 + 4

    # 4. Visitor clicks WhatsApp (+8 points)
    res2 = client.post(
        "/api/v1/visitors/events",
        json={
            "visitor_id": str(visitor.id),
            "session_id": str(session.id),
            "event_name": "whatsapp_click",
            "page": "/tours/sikkim-5d",
        },
    )
    assert res2.status_code == 201
    db_session.refresh(lead)
    assert lead.lead_score == 47  # 39 + 8

    # Verify Socket.IO updates were pushed
    assert len(score_events) == 2
    assert score_events[0] == (35, 39, 4, "ITINERARY_VIEW")
    assert score_events[1] == (39, 47, 8, "WHATSAPP_CLICK")


def test_anonymous_visitor_telemetry_no_lead_does_not_fail(client: TestClient, db_session):
    """Anonymous visitor without any Lead logs telemetry cleanly without error or score changes."""
    visitor = Visitor(visitor_code="VIS-ANON99")
    db_session.add(visitor)
    db_session.flush()

    session = VisitorSession(visitor_id=visitor.id)
    db_session.add(session)
    db_session.commit()

    res = client.post(
        "/api/v1/visitors/events",
        json={
            "visitor_id": str(visitor.id),
            "session_id": str(session.id),
            "event_name": "tour_package_view",
            "page": "/tours/darjeeling",
        },
    )
    assert res.status_code == 201
    assert res.json()["data"]["event_name"] == "tour_package_view"


# ── 5. Staff LeadActivity Scoring ─────────────────────────────────────

def test_staff_activity_logging_updates_lead_score(client: TestClient, db_session, monkeypatch):
    """Admin logs CALL / WHATSAPP activity -> Lead.lead_score increases & socket events emitted."""
    score_events = []
    activity_events = []

    def mock_emit_lead_score_updated(lead, previous_score, new_score, delta, reason):
        score_events.append((previous_score, new_score, delta, reason))

    def mock_emit_lead_activity_created(lead, activity):
        activity_events.append((lead.lead_code, activity.activity_type))

    monkeypatch.setattr("app.api.v1.admin.leads.emit_lead_score_updated", mock_emit_lead_score_updated)
    monkeypatch.setattr("app.api.v1.admin.leads.emit_lead_activity_created", mock_emit_lead_activity_created)

    enquiry = Enquiry(
        enquiry_code="ENQ-ACT01",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
        enquirer_name="Target Prospect",
    )
    db_session.add(enquiry)
    db_session.flush()

    lead = Lead(
        lead_code="LEAD-ACT01",
        enquiry_id=enquiry.id,
        full_name="Target Prospect",
        lead_score=50,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    # Log CALL (+5 points)
    res = client.post(
        f"/api/v1/admin/leads/{lead.id}/activities",
        json={
            "lead_id": str(lead.id),
            "channel": "PHONE",
            "activity_type": "CALL",
            "notes": "Discussed Sikkim itinerary with client",
        },
    )
    assert res.status_code == 201
    db_session.refresh(lead)
    assert lead.lead_score == 55
    assert len(score_events) == 1
    assert score_events[0] == (50, 55, 5, "ACTIVITY_CALL")
    assert len(activity_events) == 1
    assert activity_events[0] == ("LEAD-ACT01", "CALL")


# ── 6. Anti-Farming & Deduplication Tests ─────────────────────────────

def test_anti_farming_prevents_score_inflation(client: TestClient, db_session):
    """Rapidly repeating same package view / click does not repeatedly inflate lead score."""
    visitor = Visitor(visitor_code="VIS-FARM01")
    db_session.add(visitor)
    db_session.flush()

    session = VisitorSession(visitor_id=visitor.id)
    db_session.add(session)
    db_session.flush()

    enquiry = Enquiry(
        enquiry_code="ENQ-FARM01",
        visitor_id=visitor.id,
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()

    lead = Lead(
        lead_code="LEAD-FARM01",
        enquiry_id=enquiry.id,
        visitor_id=visitor.id,
        full_name="Farmer Prospect",
        lead_score=30,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    db_session.commit()

    # View package 1st time (+5 points -> score 35)
    client.post(
        "/api/v1/visitors/events",
        json={
            "visitor_id": str(visitor.id),
            "session_id": str(session.id),
            "event_name": "tour_package_view",
            "page": "/tours/sikkim",
            "event_metadata": {"package_id": "pkg-sikkim-1"},
        },
    )
    db_session.refresh(lead)
    assert lead.lead_score == 35

    # Spam package view 10 more times immediately
    for _ in range(10):
        client.post(
            "/api/v1/visitors/events",
            json={
                "visitor_id": str(visitor.id),
                "session_id": str(session.id),
                "event_name": "tour_package_view",
                "page": "/tours/sikkim",
                "event_metadata": {"package_id": "pkg-sikkim-1"},
            },
        )

    # Lead score should NOT increase beyond 35 because rapid duplicate events are ignored
    db_session.refresh(lead)
    assert lead.lead_score == 35


# ── 7. Admin Lead Patch & Analytics Tests ─────────────────────────────

def test_admin_patch_lead_score_and_status(client: TestClient, db_session, monkeypatch):
    """PATCH /admin/leads/{lead_id} emits status and score socket events and enforces clamping."""
    status_events = []
    score_events = []

    def mock_emit_lead_status_updated(lead, previous_status, new_status):
        status_events.append((lead.lead_code, previous_status, new_status))

    def mock_emit_lead_score_updated(lead, previous_score, new_score, delta, reason):
        score_events.append((lead.lead_code, previous_score, new_score, delta, reason))

    monkeypatch.setattr("app.api.v1.admin.leads.emit_lead_status_updated", mock_emit_lead_status_updated)
    monkeypatch.setattr("app.api.v1.admin.leads.emit_lead_score_updated", mock_emit_lead_score_updated)

    enquiry = Enquiry(
        enquiry_code="ENQ-PATCH01",
        enquiry_type=EnquiryType.FIXED_TOUR,
        channel=EnquiryChannel.WEBSITE,
    )
    db_session.add(enquiry)
    db_session.flush()

    lead = Lead(
        lead_code="LEAD-PATCH01",
        enquiry_id=enquiry.id,
        full_name="Patch Prospect",
        lead_score=40,
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    db_session.commit()

    # Update status to CONTACTED and score to 75
    res = client.patch(
        f"/api/v1/admin/leads/{lead.id}",
        json={
            "status": "CONTACTED",
            "lead_score": 75,
        },
    )
    assert res.status_code == 200
    db_session.refresh(lead)
    assert lead.status == LeadStatus.CONTACTED
    assert lead.lead_score == 75

    assert len(status_events) == 1
    assert status_events[0] == ("LEAD-PATCH01", "NEW", "CONTACTED")
    assert len(score_events) == 1
    assert score_events[0] == ("LEAD-PATCH01", 40, 75, 35, "ADMIN_MANUAL_UPDATE")


def test_analytics_overview_aggregates_lead_score(client: TestClient, db_session):
    """Analytics overview calculates average_lead_score and high_intent_count from Lead."""
    # Create test admin user
    admin_user = User(
        user_code="USR-ADMIN01",
        name="Admin Analytics Tester",
        email="admin.analytics@test.com",
        mobile="+919876543210",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.flush()

    from app.api.deps import get_current_admin_or_staff
    app.dependency_overrides[get_current_admin_or_staff] = lambda: admin_user

    # Create 2 leads: score 20, score 60 -> avg 40.0, high-intent (>=20) = 2
    enq1 = Enquiry(enquiry_code="ENQ-AN1", enquiry_type=EnquiryType.FIXED_TOUR, channel=EnquiryChannel.WEBSITE)
    enq2 = Enquiry(enquiry_code="ENQ-AN2", enquiry_type=EnquiryType.FIXED_TOUR, channel=EnquiryChannel.WEBSITE)
    db_session.add_all([enq1, enq2])
    db_session.flush()

    lead1 = Lead(lead_code="LEAD-AN1", enquiry_id=enq1.id, full_name="L1", lead_score=20)
    lead2 = Lead(lead_code="LEAD-AN2", enquiry_id=enq2.id, full_name="L2", lead_score=60)
    db_session.add_all([lead1, lead2])
    db_session.commit()

    res = client.get("/api/v1/admin/analytics/overview")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["average_lead_score"] == 40.0
    assert data["high_intent_visitors_count"] == 2

    # Test distribution breakdown
    dist_res = client.get("/api/v1/admin/analytics/lead-score-distribution")
    assert dist_res.status_code == 200
    dist_data = dist_res.json()["data"]
    assert len(dist_data) == 4
    # Range 16-30 (Hot) has 1 (lead1 with score 20), Range 31+ has 1 (lead2 with score 60)
    assert dist_data[2]["count"] == 1
    assert dist_data[3]["count"] == 1

