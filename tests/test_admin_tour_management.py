import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.enums import TourType, UserRole
from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant
from app.models.tour_detail import TourDetail
from app.models.user import User
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
    user = User(
        user_code="ADM-TOUR-001",
        name="Admin User",
        email="admin_tour@example.com",
        mobile="+919000000011",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session):
    user = User(
        user_code="STF-TOUR-001",
        name="Staff User",
        email="staff_tour@example.com",
        mobile="+919000000012",
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_token(user: User) -> str:
    return create_access_token(
        subject=user.id,
        role=user.role.value,
        actor_type=user.role.value,
        email=user.email,
        mobile=user.mobile,
    )


def create_package(db_session, *, is_active=True, is_featured=False):
    package = TourPackage(
        tour_code="T-1001",
        slug="test-tour-package",
        title="Test Tour Package",
        destination="Darjeeling",
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
        base_price=4999,
        seats=10,
        badge="Popular",
        availability="AVAILABLE",
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
        departures_dates=[{"id": "d1", "date": "2026-05-05"}],
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


def test_admin_tour_package_list_supports_is_featured_filter(client, admin_user, db_session):
    create_package(db_session, is_active=True, is_featured=False)
    featured_package = TourPackage(
        tour_code="T-1002",
        slug="featured-tour-package",
        title="Featured Tour Package",
        destination="Manali",
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


def test_staff_cannot_create_update_or_delete_tour_content(client, staff_user, db_session):
    package = create_package(db_session)
    variant = create_variant(db_session, package.id)

    auth_header = {"Authorization": f"Bearer {make_token(staff_user)}"}

    create_package_response = client.post(
        "/api/v1/admin/tour-packages",
        json={
            "tour_code": "T-9999",
            "slug": "forbidden-package",
            "title": "Forbidden Package",
            "destination": "Kashmir",
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
            "price": 3000,
            "seats": 12,
            "badge": "New",
            "availability": "AVAILABLE",
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

    create_package_response = client.post(
        "/api/v1/admin/tour-packages",
        json={
            "tour_code": "T-2001",
            "slug": "admin-created-tour",
            "title": "Admin Created Tour",
            "destination": "Sikkim",
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
            "price": 5500,
            "seats": 20,
            "badge": "Fresh",
            "availability": "AVAILABLE",
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
