import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import AccountRole
from app.models.base import Base
from app.models.account import Account
from app.models.notification import Notification
from app.models.notification_campaign import NotificationCampaign
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService

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
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_notification_and_campaign_models(db):
    # 1. Create recipient account
    account = Account(
        account_code="ACC-NOTIF-01",
        name="Notification Recipient",
        email="recipient@example.com",
        mobile="+919999988888",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # 2. Use NotificationService to create a notification
    service = NotificationService(db)
    payload = NotificationCreate(
        notification_type="PROMOTION",
        title="Exclusive Autumn Sale",
        message="Get 20% off on all North Bengal tours this season!",
        data={"campaign_name": "Autumn2026"},
    )
    notification = service.create(payload, recipient_ids=[account.id])

    # 3. Verify Notification contains the content and recipients
    assert notification.id is not None
    assert notification.title == "Exclusive Autumn Sale"
    assert notification.message == "Get 20% off on all North Bengal tours this season!"
    assert notification.notification_type == "PROMOTION"
    assert notification.recipient_ids == [account.id]

    # 4. Verify NotificationCampaign contains delivery/read metadata
    assert len(notification.campaigns) == 1
    campaign = notification.campaigns[0]
    assert campaign.notification_id == notification.id
    assert campaign.recipient_id == account.id
    assert campaign.is_delivered is True
    assert campaign.delivered_at is not None
    assert campaign.is_read is False
    assert campaign.read_at is None

    # Content accessed via relationship or response
    assert campaign.notification.title == "Exclusive Autumn Sale"
    assert campaign.notification.message == "Get 20% off on all North Bengal tours this season!"

    # 5. List for actor
    items, unread = service.list_for_actor("CUSTOMER", account.id)
    assert len(items) == 1
    assert unread == 1
    assert items[0].id == campaign.id

    # 6. Mark read
    marked = service.mark_read("CUSTOMER", account.id, campaign.id)
    assert marked is not None
    assert marked.is_read is True
    assert marked.read_at is not None

    _, unread_after = service.list_for_actor("CUSTOMER", account.id)
    assert unread_after == 0
