import csv
import io
import json

import app.models
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_admin_only
from app.api.v1.admin.promotional_contacts import router
from app.db.database import get_db
from app.models.base import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1")
        test_app.dependency_overrides[get_db] = lambda: db
        test_app.dependency_overrides[get_current_admin_only] = lambda: object()
        with TestClient(test_app) as test_client:
            yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _import_file(file_format: str) -> bytes:
    if file_format == "json":
        return json.dumps(
            [{"name": "Imported", "mobile": "9000000011", "email": "import@example.com"}]
        ).encode()
    if file_format == "csv":
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=["name", "mobile", "email"])
        writer.writeheader()
        writer.writerow(
            {"name": "Imported", "mobile": "9000000011", "email": "import@example.com"}
        )
        return output.getvalue().encode()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "mobile", "email"])
    sheet.append(["Imported", "9000000011", "import@example.com"])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_admin_can_create_read_update_search_and_delete_contacts(client):
    create = client.post(
        "/api/v1/admin/promotional-contacts",
        json={"name": "Asha", "mobile": "9000000012"},
    )
    assert create.status_code == 201
    contact_id = create.json()["data"]["id"]

    fetched = client.get(f"/api/v1/admin/promotional-contacts/{contact_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["name"] == "Asha"

    updated = client.patch(
        f"/api/v1/admin/promotional-contacts/{contact_id}",
        json={"email": "asha@example.com"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["email"] == "asha@example.com"

    cleared = client.patch(
        f"/api/v1/admin/promotional-contacts/{contact_id}",
        json={"email": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["name"] == "Asha"
    assert cleared.json()["data"]["email"] is None

    listed = client.get("/api/v1/admin/promotional-contacts?search=asha")
    assert listed.status_code == 200
    assert listed.json()["pagination"]["total_items"] == 1

    deleted = client.delete(f"/api/v1/admin/promotional-contacts/{contact_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/admin/promotional-contacts/{contact_id}").status_code == 404


@pytest.mark.parametrize("file_format", ["json", "csv", "xlsx"])
def test_admin_can_import_and_export_contacts_in_supported_formats(client, file_format):
    imported = client.post(
        f"/api/v1/admin/promotional-contacts/import?format={file_format}",
        files={"file": (f"contacts.{file_format}", _import_file(file_format))},
    )
    assert imported.status_code == 200
    assert imported.json()["data"]["imported_count"] == 1

    exported = client.get(
        f"/api/v1/admin/promotional-contacts/export?format={file_format}"
    )
    assert exported.status_code == 200
    if file_format == "json":
        assert json.loads(exported.content)[0]["name"] == "Imported"
    elif file_format == "csv":
        assert next(csv.DictReader(io.StringIO(exported.text)))["name"] == "Imported"
    else:
        workbook = load_workbook(io.BytesIO(exported.content), read_only=True)
        assert list(workbook.active.values)[1][0] == "Imported"


def test_invalid_import_is_rejected_without_partial_inserts(client):
    content = json.dumps(
        [
            {"name": "Valid", "mobile": "9000000011"},
            {"name": "Invalid", "email": "not-an-email"},
        ]
    )
    response = client.post(
        "/api/v1/admin/promotional-contacts/import?format=json",
        files={"file": ("contacts.json", content.encode())},
    )
    assert response.status_code == 422
    assert client.get("/api/v1/admin/promotional-contacts").json()["pagination"]["total_items"] == 0
