from types import SimpleNamespace
from uuid import uuid4

from app.services import hotel_service, vehicle_service


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


def test_hotel_create_and_update_do_not_include_images():
    service = hotel_service.HotelService.__new__(hotel_service.HotelService)
    service.repo = FakeHotelRepository()

    from app.schemas.hotel import HotelCreate, HotelUpdate

    service.create_hotel(HotelCreate(name="Hotel"))
    service.update_hotel(uuid4(), HotelUpdate(name="Updated Hotel"))

    assert "image" not in service.repo.created
    assert "image" not in service.repo.updated


def test_hotel_update_schema_excludes_is_active_flag():
    from app.schemas.hotel import HotelUpdate

    payload = HotelUpdate.model_validate({"name": "Updated Hotel"})
    assert "is_active" not in HotelUpdate.model_fields
    assert payload.model_dump(exclude_none=True) == {"name": "Updated Hotel"}


def test_hotel_and_vehicle_schemas_do_not_expose_images():
    from app.schemas.hotel import HotelCreate, HotelResponse, HotelUpdate
    from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

    for schema in (HotelCreate, HotelUpdate, HotelResponse):
        assert "image" not in schema.model_fields

    for schema in (VehicleCreate, VehicleUpdate, VehicleResponse):
        assert "vehicle_image" not in schema.model_fields

    assert HotelCreate.model_validate({"name": "Hotel", "image": ["legacy"]}).name == "Hotel"
    assert VehicleCreate.model_validate({"name": "Vehicle", "vehicle_image": ["legacy"]}).name == "Vehicle"


def test_vehicle_create_and_update_do_not_include_images():
    class FakeVehicleRepository:
        def __init__(self):
            self.created = None
            self.updated = None

        def create(self, **data):
            self.created = data
            return data

        def get_by_id(self, vehicle_id):
            return SimpleNamespace(id=vehicle_id, is_active=True)

        def update(self, vehicle, data):
            self.updated = data
            return data

    service = vehicle_service.VehicleService.__new__(vehicle_service.VehicleService)
    service.repo = FakeVehicleRepository()

    from app.schemas.vehicle import VehicleCreate, VehicleUpdate

    service.create_vehicle(VehicleCreate(name="Vehicle"))
    service.update_vehicle(uuid4(), VehicleUpdate(name="Updated Vehicle"))

    assert "vehicle_image" not in service.repo.created
    assert "vehicle_image" not in service.repo.updated