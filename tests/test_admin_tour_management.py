import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import TourType, AccountRole
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.destination import Destination
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.tour_detail import TourDetail
from app.models.tour_departure import TourDeparture
from app.models.account import Account
from app.utils.security import create_access_token

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
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = Account(
        account_code="ADM-TOUR-001",
        name="Admin User",
        email="admin_tour@example.com",
        mobile="+919000000011",
        role=AccountRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session):
    user = Account(
        account_code="STF-TOUR-001",
        name="Staff User",
        email="staff_tour@example.com",
        mobile="+919000000012",
        role=AccountRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_token(user: Account) -> str:
    return create_access_token(
        subject=user.id,
        role=user.role.value,
        actor_type=user.role.value,
        email=user.email,
        mobile=user.mobile,
    )


def create_package(db_session, *, is_active=True, is_featured=False):
    destination = Destination(
        name="Darjeeling",
        slug="darjeeling",
        country="India",
        is_domestic=True,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)

    package = TourPackage(
        tour_code="T-1001",
        slug="test-tour-package",
        title="Test Tour Package",
        destination_id=destination.id,
        type=TourType.DOMESTIC,
        description="Sample package",
        is_featured=is_featured,
        is_active=is_active,
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)
    return package


def create_variant(db_session, package_id, *, is_active=True):
    variant = TourVariant(
        package_id=package_id,
        slug="summer-2026",
        name="Summer Special",
        season_name="Summer",
        valid_from=date(2026, 5, 1),
        valid_to=date(2026, 5, 15),
        duration_days=5,
        duration_nights=4,
        list_price=4999,
        selling_price=4999,
        badge="Popular",
        is_default=True,
        is_active=is_active,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(variant)
    return variant


def create_detail(db_session, variant_id):
    detail = TourDetail(
        variant_id=variant_id,
        banner={"image": "https://example.com/banner.jpg", "video": None},
        gallery=[{"id": "g1", "alt": "gallery", "url": "https://example.com/1.jpg", "type": "image", "display_order": 1}],
        highlights=[{"id": "h1", "text": "Scenic route"}],
        inclusions=["Hotel stay"],
        exclusions=["Airfare"],
        itinerary=[{"id": "i1", "day": 1, "title": "Arrival", "description": "Check-in"}],
        route_stops=[{"id": "r1", "city": "Darjeeling", "nights": 1}],
    )
    db_session.add(detail)
    db_session.commit()
    db_session.refresh(detail)
    return detail


def test_staff_can_list_tour_packages_and_variant_details(client, staff_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)
    create_detail(db_session, variant.id)

    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}

    package_list = client.get("/api/v1/admin/tour-packages", headers=auth_header)
    assert package_list.status_code == 200
    assert package_list.json()["data"][0]["title"] == "Test Tour Package"

    variant_list = client.get(
        f"/api/v1/admin/tour-packages/{package.id}/variants",
        headers=auth_header,
    )
    assert variant_list.status_code == 200
    assert variant_list.json()["data"][0]["tour_id"] == str(package.id)

    detail = client.get(
        f"/api/v1/admin/tour-packages/{package.id}/variants/{variant.id}",
        headers=auth_header,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["tour_id"] == str(package.id)


def test_admin_package_variant_detail_uses_tour_departures_for_departure_dates(client, staff_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)
    create_detail(db_session, variant.id)

    departure_one = TourDeparture(
        variant_id=variant.id,
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        total_seats=12,
        available_seats=8,
        is_active=True,
    )
    departure_two = TourDeparture(
        variant_id=variant.id,
        departure_date=date(2026, 6, 12),
        return_date=date(2026, 6, 18),
        total_seats=45,
        available_seats=8,
        is_active=True,
    )
    db_session.add_all([departure_one, departure_two])
    db_session.commit()

    response = client.get(
        f"/api/v1/admin/tour-packages/{package.id}/variants/{variant.id}",
        headers={"Authorization": f"Bearer {make_token(staff_user)}"},
    )

    assert response.status_code == 200
    data = response.json()["data"]["departure_dates"]
    assert data[0]["departure_date"] == "2026-06-01"
    assert data[0]["return_date"] == "2026-06-08"
    assert data[0]["total_seats"] == 12
    assert data[0]["available_seats"] == 8
    assert data[1]["departure_date"] == "2026-06-12"
    assert data[1]["return_date"] == "2026-06-18"
    assert data[1]["total_seats"] == 45
    assert data[1]["available_seats"] == 8


def test_admin_tour_detail_create_accepts_missing_nested_ids(client, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    package = create_package(db_session)
    variant = create_variant(db_session, package.id)

    response = client.post(
        "/api/v1/admin/tour-details",
        json={
            "variant_id": str(variant.id),
            "banner": {"image": "https://example.com/banner.jpg", "video": None},
            "gallery": [{"alt": "Admin image", "url": "https://example.com/admin-1.jpg", "type": "image", "display_order": 1}],
            "highlights": [{"text": "Beautiful landscape"}],
            "inclusions": ["Meals"],
            "exclusions": ["Personal expenses"],
            "departure_dates": [{"departure_date": "2026-09-03", "return_date": "2026-09-10", "total_seats": 20, "available_seats": 20}],
            "itinerary": [{"day": 1, "title": "Arrival", "description": "Hotel check-in"}],
            "route": [{"city": "Gangtok", "nights": 2}],
        },
        headers=auth_header,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["message"] == "Tour details created successfully"
    assert response.json()["success"] is True


def test_admin_detail_banner_patch_replaces_only_supplied_media(client, admin_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)
    detail = create_detail(db_session, variant.id)
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    response = client.patch(
        f"/api/v1/admin/tour-details/{detail.id}",
        json={"banner": {"image": "https://example.com/new-banner.jpg"}},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.json()["data"]["banner"] == {
        "image": "https://example.com/new-banner.jpg",
        "video": None,
    }

    response = client.patch(
        f"/api/v1/admin/tour-details/{detail.id}",
        json={"banner": {"video": "https://example.com/banner.mp4"}},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.json()["data"]["banner"] == {
        "image": "https://example.com/new-banner.jpg",
        "video": "https://example.com/banner.mp4",
    }


def test_admin_detail_banner_ignores_extra_media_fields(client, admin_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)
    detail = create_detail(db_session, variant.id)

    response = client.patch(
        f"/api/v1/admin/tour-details/{detail.id}",
        json={"banner": {"image": "https://example.com/new-banner.jpg", "thumbnail": "extra"}},
        headers={"Authorization": f"Bearer {make_token(admin_user)}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["banner"] == {
        "image": "https://example.com/new-banner.jpg",
        "video": None,
    }


def test_admin_detail_get_normalizes_legacy_highlight_strings(client, staff_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)
    detail = TourDetail(
        variant_id=variant.id,
        banner={"image": "https://example.com/banner.jpg"},
        gallery=[],
        highlights=["Dal Lake shikara ride", "Gulmarg Gondola"],
        inclusions=[],
        exclusions=[],
        itinerary=[],
        route_stops=[],
    )
    db_session.add(detail)
    db_session.commit()

    response = client.get(
        f"/api/v1/admin/tour-details/{detail.id}",
        headers={"Authorization": f"Bearer {make_token(staff_user)}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["highlights"] == [
        {"id": "h1", "text": "Dal Lake shikara ride"},
        {"id": "h2", "text": "Gulmarg Gondola"},
    ]


def test_admin_tour_package_creation_rejects_unknown_destination_id(client, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    missing_destination_id = uuid.uuid4()

    response = client.post(
        "/api/v1/admin/tour-packages",
        headers=auth_header,
        json={
            "tour_code": "T-4041",
            "slug": "unknown-destination-package",
            "title": "Unknown Destination Package",
            "destination_id": str(missing_destination_id),
            "type": "DOMESTIC",
            "description": "Should be rejected",
            "is_featured": False,
            "is_active": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "Destination" in response.json()["message"]


def test_admin_tour_package_update_uses_destination_id_only(client, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    old_destination = Destination(name="Old Destination", slug="old-destination", country="India", is_domestic=True)
    new_destination = Destination(name="New Destination", slug="new-destination", country="India", is_domestic=True)
    db_session.add_all([old_destination, new_destination])
    db_session.commit()
    db_session.refresh(old_destination)
    db_session.refresh(new_destination)

    package = TourPackage(
        tour_code="T-4042",
        slug="destination-id-only-update",
        title="Destination ID Only Update",
        destination_id=old_destination.id,
        type=TourType.DOMESTIC,
        description="Package with destination relation",
        is_featured=False,
        is_active=True,
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)

    response = client.patch(
        f"/api/v1/admin/tour-packages/{package.id}",
        headers=auth_header,
        json={
            "destination_id": str(new_destination.id),
            "destination": {"id": str(old_destination.id), "name": "Ignored Destination"},
            "title": "Destination ID Only Updated",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Tour package updated successfully"

    db_session.refresh(package)
    assert package.destination_id == new_destination.id
    assert package.title == "Destination ID Only Updated"


def test_admin_tour_package_list_supports_type_filter(client, admin_user, db_session):
    create_package(db_session, is_active=True, is_featured=False)
    destination = Destination(
        name="Ladakh",
        slug="ladakh",
        country="India",
        is_domestic=False,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)

    international_package = TourPackage(
        tour_code="T-1002",
        slug="international-tour-package",
        title="International Tour Package",
        destination_id=destination.id,
        type=TourType.INTERNATIONAL,
        description="International package",
        is_featured=False,
        is_active=True,
    )
    db_session.add(international_package)
    db_session.commit()
    db_session.refresh(international_package)

    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    response = client.get("/api/v1/admin/tour-packages?type=INTERNATIONAL", headers=auth_header)

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(international_package.id)
    assert items[0]["type"] == "INTERNATIONAL"
    assert items[0]["destination"] == "Ladakh"
    assert items[0]["destination_id"] == str(destination.id)


def test_admin_tour_package_list_supports_destination_id_filter(client, admin_user, db_session):
    matching_destination = Destination(
        name="Goa",
        slug="goa-admin-filter",
        country="India",
        is_domestic=True,
    )
    other_destination = Destination(
        name="Jaipur",
        slug="jaipur-admin-filter",
        country="India",
        is_domestic=True,
    )
    db_session.add_all([matching_destination, other_destination])
    db_session.commit()
    db_session.refresh(matching_destination)
    db_session.refresh(other_destination)

    matching_package = TourPackage(
        tour_code="T-1005",
        slug="goa-filter-package",
        title="Goa Filter Package",
        destination_id=matching_destination.id,
        type=TourType.DOMESTIC,
        is_featured=False,
        is_active=True,
    )
    other_package = TourPackage(
        tour_code="T-1006",
        slug="jaipur-filter-package",
        title="Jaipur Filter Package",
        destination_id=other_destination.id,
        type=TourType.DOMESTIC,
        is_featured=False,
        is_active=True,
    )
    db_session.add_all([matching_package, other_package])
    db_session.commit()

    response = client.get(
        f"/api/v1/admin/tour-packages?destination_id={matching_destination.id}",
        headers={"Authorization": f"Bearer {make_token(admin_user)}"},
    )

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(matching_package.id)
    assert items[0]["destination_id"] == str(matching_destination.id)


def test_admin_tour_package_list_supports_is_featured_filter(client, admin_user, db_session):
    create_package(db_session, is_active=True, is_featured=False)
    destination = Destination(
        name="Manali",
        slug="manali",
        country="India",
        is_domestic=True,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)

    featured_package = TourPackage(
        tour_code="T-1003",
        slug="featured-tour-package",
        title="Featured Tour Package",
        destination_id=destination.id,
        type=TourType.DOMESTIC,
        description="Featured package",
        is_featured=True,
        is_active=True,
    )
    db_session.add(featured_package)
    db_session.commit()
    db_session.refresh(featured_package)

    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    response = client.get("/api/v1/admin/tour-packages?is_featured=true", headers=auth_header)

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(featured_package.id)
    assert items[0]["is_featured"] is True


def test_admin_tour_package_list_handles_package_without_destination_relation(client, admin_user, db_session):
    package = TourPackage(
        tour_code="T-1004",
        slug="no-destination-package",
        title="No Destination Package",
        destination_id=None,
        type=TourType.DOMESTIC,
        description="Package without linked destination",
        is_featured=False,
        is_active=True,
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)

    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}
    response = client.get("/api/v1/admin/tour-packages", headers=auth_header)

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) >= 1
    assert any(item["id"] == str(package.id) for item in items)


def test_staff_cannot_create_update_or_delete_tour_content(client, staff_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)

    destination = Destination(
        name="Kashmir",
        slug="kashmir",
        country="India",
        is_domestic=True,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)

    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}

    create_package_response = client.post(
        "/api/v1/admin/tour-packages",
        json={
            "tour_code": "T-9999",
            "slug": "forbidden-package",
            "title": "Forbidden Package",
            "destination_id": str(destination.id),
            "type": "DOMESTIC",
            "description": "Nope",
            "is_featured": False,
            "is_active": True,
        },
        headers=auth_header,
    )
    assert create_package_response.status_code == 403

    update_package_response = client.patch(
        f"/api/v1/admin/tour-packages/{package.id}",
        json={"title": "Updated Title"},
        headers=auth_header,
    )
    assert update_package_response.status_code == 403

    create_variant_response = client.post(
        "/api/v1/admin/tour-variants",
        json={
            "tour_id": str(package.id),
            "slug": "forbidden-variant",
            "name": "Forbidden Variant",
            "season_name": "Monsoon",
            "valid_from": "2026-07-01",
            "valid_to": "2026-07-10",
            "duration_days": 4,
            "duration_nights": 3,
            "list_price": 3000,
            "selling_price": 3000,
            "badge": "New",
            "is_default": False,
            "is_active": True,
        },
        headers=auth_header,
    )
    assert create_variant_response.status_code == 403

    update_variant_response = client.patch(
        f"/api/v1/admin/tour-variants/{variant.id}",
        json={"name": "Updated Variant Name"},
        headers=auth_header,
    )
    assert update_variant_response.status_code == 403

    delete_variant_response = client.delete(
        f"/api/v1/admin/tour-variants/{variant.id}",
        headers=auth_header,
    )
    assert delete_variant_response.status_code == 403


def test_admin_can_create_update_and_delete_tour_package_variant_and_detail(client, admin_user, db_session):
    auth_header = {"Authorization": f"Bearer {make_token(admin_user)}"}

    destination = Destination(
        name="Sikkim",
        slug="sikkim",
        country="India",
        is_domestic=True,
    )
    db_session.add(destination)
    db_session.commit()
    db_session.refresh(destination)

    create_package_response = client.post(
        "/api/v1/admin/tour-packages",
        json={
            "tour_code": "T-2001",
            "slug": "admin-created-tour",
            "title": "Admin Created Tour",
            "destination_id": str(destination.id),
            "type": "DOMESTIC",
            "description": "Created by admin",
            "is_featured": True,
            "is_active": True,
        },
        headers=auth_header,
    )
    assert create_package_response.status_code == 201
    package_id = client.get("/api/v1/admin/tour-packages?search=admin-created-tour", headers=auth_header).json()["data"][0]["id"]

    create_variant_response = client.post(
        "/api/v1/admin/tour-variants",
        json={
            "tour_id": package_id,
            "slug": "admin-created-variant",
            "name": "Admin Created Variant",
            "season_name": "Autumn",
            "valid_from": "2026-09-01",
            "valid_to": "2026-09-08",
            "duration_days": 6,
            "duration_nights": 5,
            "list_price": 5500,
            "selling_price": 5500,
            "badge": "Fresh",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_header,
    )
    assert create_variant_response.status_code == 201
    variant_id = client.get(f"/api/v1/admin/tour-variants?tour_id={package_id}", headers=auth_header).json()["data"][0]["id"]

    create_detail_response = client.post(
        "/api/v1/admin/tour-details",
        json={
            "variant_id": variant_id,
            "banner": {"image": "https://example.com/admin-banner.jpg", "video": None},
            "gallery": [{"id": "a1", "alt": "Admin image", "url": "https://example.com/admin-1.jpg", "type": "image", "display_order": 1}],
            "highlights": [{"id": "h1", "text": "Beautiful landscape"}],
            "inclusions": ["Meals"],
            "exclusions": ["Personal expenses"],
            "departure_dates": [{"id": "d1", "date": "2026-09-03"}],
            "itinerary": [{"id": "i1", "day": 1, "title": "Arrival", "description": "Hotel check-in"}],
            "route": [{"id": "r1", "city": "Gangtok", "nights": 2}],
        },
        headers=auth_header,
    )
    assert create_detail_response.status_code == 201

    update_package_response = client.patch(
        f"/api/v1/admin/tour-packages/{package_id}",
        json={"title": "Updated Admin Tour"},
        headers=auth_header,
    )
    assert update_package_response.status_code == 200
    assert update_package_response.json()["message"] == "Tour package updated successfully"

    update_variant_response = client.patch(
        f"/api/v1/admin/tour-variants/{variant_id}",
        json={"name": "Updated Variant"},
        headers=auth_header,
    )
    assert update_variant_response.status_code == 200
    assert update_variant_response.json()["message"] == "Tour variant updated successfully"

    detail_id = client.get(
        f"/api/v1/admin/tour-packages/{package_id}/variants/{variant_id}",
        headers=auth_header,
    ).json()["data"]["id"]
    update_detail_response = client.patch(
        f"/api/v1/admin/tour-details/{detail_id}",
        json={"highlights": [{"id": "h1", "text": "Updated highlight"}]},
        headers=auth_header,
    )
    assert update_detail_response.status_code == 200
    assert update_detail_response.json()["message"] == "Tour details updated successfully"

    delete_detail_response = client.delete(
        f"/api/v1/admin/tour-details/{detail_id}",
        headers=auth_header,
    )
    assert delete_detail_response.status_code == 200

    delete_variant_response = client.delete(
        f"/api/v1/admin/tour-variants/{variant_id}",
        headers=auth_header,
    )
    assert delete_variant_response.status_code == 200

    delete_package_response = client.delete(
        f"/api/v1/admin/tour-packages/{package_id}",
        headers=auth_header,
    )
    assert delete_package_response.status_code == 200
