import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_actor
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_upload_requires_jwt(client: TestClient):
    response = client.post(
        "/api/v1/public/files/upload",
        files={"file": ("photo.jpg", b"content", "image/jpeg")},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("actor_type", ["ADMIN", "STAFF", "CUSTOMER"])
def test_upload_accepts_authenticated_actor(
    client: TestClient,
    monkeypatch,
    actor_type: str,
):
    app.dependency_overrides[get_current_actor] = lambda: (object(), actor_type)

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
    try:
        response = client.post(
            "/api/v1/public/files/upload",
            files={"file": ("photo.jpg", b"content", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_current_actor, None)

    assert response.status_code == 201
    assert response.json()["data"]["public_id"] == "tour-packages/photo"