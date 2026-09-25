from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services import hotel_service


class FakeHotelRepository:
    def __init__(self):
        self.created = None
        self.updated = None

    def destination_exists(self, destination_id):
        return True

    def create(self, **data):
        self.created = data
        return data

    def get_by_id(self, hotel_id):
        return SimpleNamespace(id=hotel_id, is_active=True)

    def update(self, hotel, data):
        self.updated = data
        return data


@pytest.mark.anyio
async def test_hotel_create_and_update_promote_gallery_urls(monkeypatch):
    promoted_urls = []

    async def fake_promote(url, target_folder, resource_type):
        promoted_urls.append((url, target_folder, resource_type))
        return {"url": f"permanent/{url.rsplit('/', 1)[-1]}", "public_id": ""}

    monkeypatch.setattr(hotel_service, "promote_cloudinary_asset", fake_promote)
    service = hotel_service.HotelService.__new__(hotel_service.HotelService)
    service.repo = FakeHotelRepository()

    image = {"id": "image-1", "alt": "Lobby", "url": "temporary/lobby.jpg", "type": "image"}
    payload = SimpleNamespace(
        destination_id=None,
        model_dump=lambda: {
            "name": "Hotel",
            "image": [image],
            "destination_id": None,
        },
    )
    await service.create_hotel(payload)

    update_payload = SimpleNamespace(
        model_dump=lambda **kwargs: {
            "image": [{"id": "image-2", "url": "temporary/room.jpg", "type": "image"}],
        },
    )
    await service.update_hotel(uuid4(), update_payload)

    assert promoted_urls == [
        ("temporary/lobby.jpg", "hotel-images", "image"),
        ("temporary/room.jpg", "hotel-images", "image"),
    ]
    assert service.repo.created["image"][0]["url"] == "permanent/lobby.jpg"
    assert service.repo.updated["image"][0]["url"] == "permanent/room.jpg"


def test_hotel_update_schema_excludes_is_active_flag():
    from app.schemas.hotel import HotelUpdate

    payload = HotelUpdate.model_validate({"name": "Updated Hotel"})
    assert "is_active" not in HotelUpdate.model_fields
    assert payload.model_dump(exclude_none=True) == {"name": "Updated Hotel"}