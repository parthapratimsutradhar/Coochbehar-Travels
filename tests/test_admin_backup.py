import json
import uuid
from io import BytesIO
from datetime import date
from decimal import Decimal

import app.models
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.admin.backup import router as admin_backup_router
from app.api.deps import get_current_admin_only
from app.core.enums import AccountRole, TourType, VehicleType
from app.models.account import Account
from app.models.base import Base
from app.models.customer_profile import CustomerProfile
from app.models.destination import Destination
from app.models.hotel import Hotel
from app.models.tour_detail import TourDetail
from app.models.tour_departure import TourDeparture
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.vehicle import Vehicle
from app.models.vendor import Vendor
from app.services.backup_service import BackupService
from app.schemas.response import ActionResponse
from app.core.exception_handlers import register_exception_handlers
from app.db.database import get_db


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def add_backup_records(db: Session) -> None:
    destination = Destination(name="Darjeeling", slug="darjeeling-backup", country="India")
    customer = Account(
        account_code="C-BACKUP-1",
        name="Backup Customer",
        role=AccountRole.CUSTOMER,
        email="backup-customer@example.com",
    )
    staff = Account(
        account_code="S-BACKUP-1",
        name="Backup Staff",
        role=AccountRole.STAFF,
        email="backup-staff@example.com",
    )
    admin = Account(
        account_code="A-BACKUP-1",
        name="Backup Admin",
        role=AccountRole.ADMIN,
        email="backup-admin@example.com",
    )
    db.add_all([destination, customer, staff, admin])
    db.flush()
    customer_profile = CustomerProfile(
        account_id=customer.id,
        referral_code="BACKUP-CUSTOMER",
        address="Coochbehar",
    )
    package = TourPackage(
        tour_code="T-BACKUP-1",
        slug="darjeeling-backup-tour",
        title="Darjeeling Tour",
        destination_id=destination.id,
        type=TourType.DOMESTIC,
    )
    db.add_all([customer_profile, package])
    db.flush()
    variant = TourVariant(
        package_id=package.id,
        slug="darjeeling-backup-tour-standard",
        name="Standard",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        duration_days=3,
        duration_nights=2,
        list_price=Decimal("15000.00"),
        selling_price=Decimal("12500.00"),
    )
    db.add(variant)
    db.flush()
    db.add(
        TourDeparture(
            variant_id=variant.id,
            departure_date=date(2026, 10, 17),
            return_date=date(2026, 10, 25),
            total_seats=20,
            available_seats=12,
        )
    )
    db.add_all(
        [
            TourDetail(
                variant_id=variant.id,
                banner={"url": "banner.jpg"},
                gallery=[],
                highlights=[{"title": "Tea gardens"}],
                inclusions=["Breakfast"],
                exclusions=[],
                itinerary=[{"day": 1, "title": "Arrival"}],
                route_stops=[],
            ),
            Hotel(name="Backup Hotel", image=[], destination_id=destination.id),
            Vendor(name="Backup Vendor", type="HOTEL", email="vendor@example.com"),
            Vehicle(
                name="Backup Vehicle",
                vehicle_image=[],
                vehicle_type=VehicleType.ANY,
                capacity=4,
                price_per_day=Decimal("2000.00"),
            ),
        ]
    )
    db.commit()


def test_import_endpoint_uses_action_response():
    import_route = next(
        route for route in admin_backup_router.routes if route.path.endswith("/import")
    )
    assert import_route.response_model is ActionResponse


@pytest.mark.parametrize("format", ["json", "csv", "xlsx"])
def test_backup_round_trip_preserves_selected_relationships(db: Session, format: str):
    add_backup_records(db)
    groups = ["customers", "staff", "tours", "hotels", "vendors", "vehicles"]
    content, _, _ = BackupService(db).export(groups, format)
    if format == "json":
        manifest = json.loads(content)
        assert manifest["tables"]["tour_departures"] == [
            {
                "variant_id": str(db.scalar(select(TourVariant)).id),
                "departure_date": "2026-10-17",
                "return_date": "2026-10-25",
                "total_seats": 20,
                "available_seats": 12,
                "id": manifest["tables"]["tour_departures"][0]["id"],
                "created_at": manifest["tables"]["tour_departures"][0]["created_at"],
                "updated_at": manifest["tables"]["tour_departures"][0]["updated_at"],
                "is_active": True,
            }
        ]
    if format == "xlsx":
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        active_sheet = workbook.active
        rows = active_sheet.iter_rows(values_only=True)
        assert active_sheet.title == "tour_overview"
        columns = next(rows)
        record = dict(zip(columns, next(rows)))
        assert record["tour_title"] == "Darjeeling Tour"
        assert record["destination_name"] == "Darjeeling"
        assert record["variant_name"] == "Standard"
        assert json.loads(record["itinerary"]) == [{"day": 1, "title": "Arrival"}]
        workbook.close()

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=target_engine)
    with Session(target_engine) as target:
        imported = BackupService(target).import_backup(content, format)
        assert imported == {"inserted": 11, "updated": 0}
        assert target.scalar(select(Account).where(Account.role == AccountRole.ADMIN)) is None
        assert target.scalar(select(CustomerProfile)).account.name == "Backup Customer"
        detail = target.scalar(select(TourDetail))
        assert detail.variant.package.destination.name == "Darjeeling"
        assert detail.itinerary == [{"day": 1, "title": "Arrival"}]
        departure = target.scalar(select(TourDeparture))
        assert departure.departure_date == date(2026, 10, 17)
        assert departure.return_date == date(2026, 10, 25)
        assert departure.total_seats == 20
        assert departure.available_seats == 12
        assert target.scalar(select(Hotel)).destination_ref.name == "Darjeeling"

        package = target.scalar(select(TourPackage))
        package.title = "Database version"
        departure.available_seats = 5
        target.flush()
        second_import = BackupService(target).import_backup(content, format)
        assert second_import == {"inserted": 0, "updated": 0}
        assert package.title == "Database version"
        assert departure.available_seats == 5
    target_engine.dispose()


def test_backup_import_rejects_admin_account_records_without_partial_write(db: Session):
    admin = Account(
        account_code="A-IMPORT-1",
        name="Must Not Import",
        role=AccountRole.ADMIN,
        email="must-not-import@example.com",
    )
    db.add(admin)
    db.flush()
    manifest = {
        "format": "ct-admin-backup",
        "version": 1,
        "groups": ["staff"],
        "tables": {"accounts": [BackupService._serialize_model(admin)]},
    }

    with pytest.raises(ValueError, match="Admin accounts cannot be imported"):
        BackupService(db).import_backup(json.dumps(manifest).encode(), "json")
    assert db.scalar(select(Account)) is None


def test_backup_import_skips_existing_unique_values_with_different_id(db: Session):
    destination = Destination(name="Database version", slug="shared-destination")
    db.add(destination)
    db.flush()
    backup_row = BackupService._serialize_model(destination)
    backup_row["id"] = str(uuid.uuid4())
    backup_row["name"] = "Backup version"
    manifest = {
        "format": "ct-admin-backup",
        "version": 1,
        "groups": ["destinations"],
        "tables": {"destinations": [backup_row]},
    }

    result = BackupService(db).import_backup(json.dumps(manifest).encode(), "json")

    assert result == {"inserted": 0, "updated": 0}
    assert db.scalar(select(Destination)).name == "Database version"
    assert len(db.scalars(select(Destination)).all()) == 1


def test_backup_import_remaps_foreign_keys_for_duplicate_tour_rows(db: Session):
    destination = Destination(name="Egypt", slug="egypt-remap")
    db.add(destination)
    db.flush()
    package = TourPackage(
        tour_code="EGYPT-REMAP",
        slug="egypt-remap-tour",
        title="Egypt Tour",
        destination_id=destination.id,
        type=TourType.INTERNATIONAL,
    )
    db.add(package)
    db.flush()
    variant = TourVariant(
        package_id=package.id,
        slug="egypt-remap-variant",
        name="Standard",
        valid_from=date(2026, 10, 17),
        valid_to=date(2026, 10, 25),
        duration_days=9,
        duration_nights=8,
        list_price=Decimal("95000.00"),
        selling_price=Decimal("95000.00"),
        is_default=True,
    )
    db.add(variant)
    db.flush()
    detail = TourDetail(
        variant_id=variant.id,
        banner={},
        gallery=[],
        highlights=[],
        inclusions=[],
        exclusions=[],
        itinerary=[],
        route_stops=[],
    )
    departure = TourDeparture(
        variant_id=variant.id,
        departure_date=date(2026, 10, 17),
        return_date=date(2026, 10, 25),
        total_seats=20,
        available_seats=12,
    )
    db.add_all([detail, departure])
    db.flush()

    backup_destination_id = uuid.uuid4()
    backup_package_id = uuid.uuid4()
    backup_variant_id = uuid.uuid4()
    destination_row = BackupService._serialize_model(destination)
    destination_row["id"] = str(backup_destination_id)
    package_row = BackupService._serialize_model(package)
    package_row["id"] = str(backup_package_id)
    package_row["destination_id"] = str(backup_destination_id)
    variant_row = BackupService._serialize_model(variant)
    variant_row["id"] = str(backup_variant_id)
    variant_row["package_id"] = str(backup_package_id)
    detail_row = BackupService._serialize_model(detail)
    detail_row["id"] = str(uuid.uuid4())
    detail_row["variant_id"] = str(backup_variant_id)
    departure_row = BackupService._serialize_model(departure)
    departure_row["id"] = str(uuid.uuid4())
    departure_row["variant_id"] = str(backup_variant_id)
    manifest = {
        "format": "ct-admin-backup",
        "version": 1,
        "groups": ["tours"],
        "tables": {
            "destinations": [destination_row],
            "tour_packages": [package_row],
            "tour_variants": [variant_row],
            "tour_details": [detail_row],
            "tour_departures": [departure_row],
        },
    }

    result = BackupService(db).import_backup(json.dumps(manifest).encode(), "json")

    assert result == {"inserted": 0, "updated": 0}
    assert len(db.scalars(select(Destination)).all()) == 1
    assert len(db.scalars(select(TourPackage)).all()) == 1
    assert len(db.scalars(select(TourVariant)).all()) == 1
    assert len(db.scalars(select(TourDetail)).all()) == 1
    assert len(db.scalars(select(TourDeparture)).all()) == 1
    assert db.scalar(select(TourPackage)).destination_id == destination.id
    assert db.scalar(select(TourVariant)).package_id == package.id
    assert db.scalar(select(TourDeparture)).variant_id == variant.id


def test_backup_import_conflict_response_includes_database_field():
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(admin_backup_router, prefix="/api/v1")
    test_app.dependency_overrides[get_current_admin_only] = lambda: object()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    test_app.dependency_overrides[get_db] = override_get_db
    manifest = {
        "format": "ct-admin-backup",
        "version": 1,
        "groups": ["destinations"],
        "tables": {
            "destinations": [
                {"id": str(uuid.uuid4()), "name": None, "slug": "missing-name"}
            ]
        },
    }

    with TestClient(test_app) as client:
        response = client.post(
            "/api/v1/admin/backups/import",
            files={"file": ("backup.json", json.dumps(manifest), "application/json")},
        )
    engine.dispose()

    assert response.status_code == 409
    assert response.json()["error"]["details"] == {
        "reason": "not_null_violation",
        "table": "destinations",
        "column": "name",
    }