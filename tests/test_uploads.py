import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_upload_requires_upload_key(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "UPLOAD_KEY", "test-upload-key")

    response = client.post(
        "/api/v1/public/files/upload?sub_folder=tour-packages",
        files={"file": ("photo.jpg", b"content", "image/jpeg")},
    )

    assert response.status_code == 401


def test_upload_accepts_configured_upload_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "UPLOAD_KEY", "test-upload-key")

    async def fake_upload_file_to_cloudinary(file, sub_folder):
        return {
            "secure_url": "https://res.cloudinary.com/example/image/upload/photo.jpg",
            "public_id": "tour-packages/photo",
            "folder": "Coochbehar-travels/tour-packages",
            "resource_type": "image",
            "format": "jpg",
            "bytes": 7,
        }

    monkeypatch.setattr(
        "app.api.v1.public.uploads.upload_file_to_cloudinary",
        fake_upload_file_to_cloudinary,
    )

    response = client.post(
        "/api/v1/public/files/upload?sub_folder=tour-packages",
        headers={"X-Upload-Key": "test-upload-key"},
        files={"file": ("photo.jpg", b"content", "image/jpeg")},
    )

    assert response.status_code == 201
    assert response.json()["public_id"] == "tour-packages/photo"