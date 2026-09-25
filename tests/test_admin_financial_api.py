import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

from app.core.enums import AccountRole, FinancialTransactionType
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.utils.security import create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


def make_token(user: Account) -> str:
    return create_access_token(subject=user.id, role=user.role.value)


def setup_db():
    Base.metadata.create_all(bind=test_engine)
    user = Account(
        account_code="ADM-FIN-001",
        name="Finance Admin",
        email="finance-admin@example.com",
        mobile="+919000000099",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    session = TestingSessionLocal()
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return user


def test_admin_financial_transactions_and_reports_flow():
    user = setup_db()
    headers = {"Authorization": f"Bearer {make_token(user)}"}

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/admin/financial/transactions",
            json={
                "transaction_type": FinancialTransactionType.BOOKING_PAYMENT.value,
                "amount": "2500.50",
                "category": "booking_income",
                "description": "Tour booking payment",
                "transaction_date": "2026-09-01T10:30:00",
                "creditor": "Customer",
                "debtor": "Platform",
                "status": "POSTED",
            },
            headers=headers,
        )
        assert create_response.status_code == 201, create_response.text
        data = create_response.json()["data"]
        assert data["amount"] == "2500.50"
        assert data["category"] == "booking_income"

        list_response = client.get(
            "/api/v1/admin/financial/transactions?transaction_type=BOOKING_PAYMENT&search=booking",
            headers=headers,
        )
        assert list_response.status_code == 200, list_response.text
        assert list_response.json()["data"][0]["category"] == "booking_income"

        stats_response = client.get(
            "/api/v1/admin/financial/statistics?period=monthly&start_date=2026-09-01&end_date=2026-09-30",
            headers=headers,
        )
        assert stats_response.status_code == 200, stats_response.text
        assert stats_response.json()["data"]["total_income"] == "2500.50"

        report_response = client.get(
            "/api/v1/admin/financial/reports?report_type=income&start_date=2026-09-01&end_date=2026-09-30",
            headers=headers,
        )
        assert report_response.status_code == 200, report_response.text
        assert report_response.json()["data"]["totals"]["income"] == "2500.50"

        download_response = client.post(
            "/api/v1/admin/financial/download",
            json={"format": "csv", "report_type": "income", "period": "monthly", "start_date": "2026-09-01", "end_date": "2026-09-30"},
            headers=headers,
        )
        assert download_response.status_code == 200, download_response.text
        assert download_response.headers["content-type"].startswith("text/csv")

        update_response = client.put(
            f"/api/v1/admin/financial/transactions/{data['id']}",
            json={"amount": "3000.00", "description": "Updated booking payment"},
            headers=headers,
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["data"]["amount"] == "3000.00"

        delete_response = client.delete(
            f"/api/v1/admin/financial/transactions/{data['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 200, delete_response.text
        assert delete_response.json()["message"] == "Financial transaction deleted successfully"
