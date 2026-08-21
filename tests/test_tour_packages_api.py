from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.review import Review
from app.models.tour_detail import TourDetail
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def setup_db():
    Base.metadata.create_all(bind=test_engine)


def override_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_package_and_variants():
    session = TestingSessionLocal()
    package = TourPackage(
        tour_code="TP-1001",
        slug="himachal-summer",
        title="Himachal Summer Escape",
        destination="Himachal Pradesh",
        type="DOMESTIC",
        description="A relaxed summer getaway.",
        is_featured=True,
    )
    session.add(package)
    session.flush()

    default_variant = TourVariant(
        package_id=package.id,
        slug="family-summer",
        name="Family Summer",
        season_name="Summer Special",
        badge="Most Popular",
        valid_from=date(2026, 4, 1),
        valid_to=date(2026, 6, 30),
        duration_days=5,
        duration_nights=4,
        base_price=2499,
        seats=10,
        availability="AVAILABLE",
        is_default=True,
        is_active=True,
    )
    session.add(default_variant)
    session.flush()

    alt_variant = TourVariant(
        package_id=package.id,
        slug="honeymoon-summer",
        name="Honeymoon Summer",
        season_name="Couple Retreat",
        badge="Top Rated",
        valid_from=date(2026, 5, 1),
        valid_to=date(2026, 7, 15),
        duration_days=6,
        duration_nights=5,
        base_price=3299,
        seats=8,
        availability="AVAILABLE",
        is_default=False,
        is_active=True,
    )
    session.add(alt_variant)
    session.flush()

    session.add(
        TourDetail(
            variant_id=default_variant.id,
            banner={"url": "https://example.com/default-banner.jpg"},
            gallery=[{"url": "https://example.com/img1.jpg"}],
            highlights=[{"text": "Snow views"}],
            inclusions=["Stay", "Meals"],
            exclusions=["Flights"],
            departures_dates=[{"date": "2026-05-12"}],
            itinerary=[{"day": 1, "description": "Arrival"}],
            route_stops=[{"name": "Shimla"}],
        )
    )
    session.add(
        TourDetail(
            variant_id=alt_variant.id,
            banner={"url": "https://example.com/alt-banner.jpg"},
            gallery=[{"url": "https://example.com/img2.jpg"}],
            highlights=[{"text": "Private cab"}],
            inclusions=["Stay", "Meals"],
            exclusions=["Flights"],
            departures_dates=[{"date": "2026-05-20"}],
            itinerary=[{"day": 1, "description": "Arrival"}],
            route_stops=[{"name": "Manali"}],
        )
    )

    session.add(
        Review(
            review_code="REV-1001",
            package_id=package.id,
            customer_id=None,
            name="Alak Pandey",
            rating=5,
            review="Amazing experience.",
            review_gallery=[],
            is_verified=True,
            is_published=True,
        )
    )
    session.commit()
    return package


def test_tour_package_endpoints_return_default_variant_data():
    setup_db()
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    create_package_and_variants()

    list_response = client.get(
        "/api/v1/tour-packages",
        params={"destination": "Himachal", "type": "DOMESTIC"},
    )
    assert list_response.status_code == 200
    body = list_response.json()
    first_item = body["data"][0]
    assert first_item["destination"] == "Himachal Pradesh"
    assert first_item["season_name"] == "Summer Special"
    assert first_item["badge"] == "Most Popular"
    assert first_item["banner"] == "https://example.com/default-banner.jpg"

    detail_response = client.get("/api/v1/tour-packages/himachal-summer")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()["data"]
    assert detail_data["default_variant"]["season_name"] == "Summer Special"
    assert len(detail_data["other_variants"]) == 1

    variant_response = client.get(
        "/api/v1/tour-packages/himachal-summer/variants/honeymoon-summer"
    )
    assert variant_response.status_code == 200
    variant_data = variant_response.json()["data"]
    assert variant_data["variant"]["slug"] == "honeymoon-summer"
    assert variant_data["variant"]["season_name"] == "Couple Retreat"
    assert variant_data["variant"]["badge"] == "Top Rated"
    assert len(variant_data["other_variants"]) == 1

    app.dependency_overrides.clear()
