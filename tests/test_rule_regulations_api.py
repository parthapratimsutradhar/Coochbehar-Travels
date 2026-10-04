import json
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

import app.models
from app.api.deps import get_current_admin_only
from app.core.enums import AccountRole
from app.db.database import get_db
from app.main import fastapi_app as app
from app.models.account import Account
from app.models.base import Base


compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(PG_ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")
sqlite3.register_adapter(list, lambda value: json.dumps([str(item) for item in value]))

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_admin_manages_rules_and_public_fetch_filters_by_type():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin = Account(
        account_code="ADMIN-RULE-01",
        name="Rules Admin",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin_only] = lambda: admin
    try:
        with TestClient(app) as client:
            domestic_create = client.post(
                "/api/v1/admin/rules-regulations",
                json={
                    "rule_title": "Domestic baggage rules",
                    "regulations": [{"title": "Baggage", "items": ["One checked bag"]}],
                    "type": "DOMESTIC",
                },
            )
            international_create = client.post(
                "/api/v1/admin/rules-regulations",
                json={
                    "rule_title": "International visa rules",
                    "regulations": {"documents": ["Passport", "Visa"]},
                    "type": "INTERNATIONAL",
                },
            )
            domestic_public = client.get("/api/v1/rules-regulations?type=dom")
            international_public = client.get("/api/v1/rules-regulations?type=int")
            invalid_public = client.get("/api/v1/rules-regulations?type=other")
            admin_list = client.get("/api/v1/admin/rules-regulations")
            enduser_openapi = client.get("/openapi/enduser.json")

            item_id = admin_list.json()["data"][0]["id"]
            update_response = client.patch(
                f"/api/v1/admin/rules-regulations/{item_id}",
                json={"is_active": False},
            )
            domestic_after_deactivation = client.get("/api/v1/rules-regulations?type=dom")
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)

    assert domestic_create.status_code == 201
    assert international_create.status_code == 201
    assert domestic_public.status_code == 200
    assert len(domestic_public.json()["data"]) == 1
    assert domestic_public.json()["data"][0]["regulations"] == [
        {"title": "Baggage", "items": ["One checked bag"]}
    ]
    assert international_public.status_code == 200
    assert len(international_public.json()["data"]) == 1
    assert invalid_public.status_code == 422
    assert admin_list.status_code == 200
    assert len(admin_list.json()["data"]) == 2
    assert "/api/v1/rules-regulations" in enduser_openapi.json()["paths"]
    assert update_response.status_code == 200
    assert domestic_after_deactivation.json()["data"] == []