from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_customer
from app.core.enums import AccountRole
from app.db.database import get_db
from app.main import app
from app.models.account import Account
from app.models.base import Base
from app.models.destination import Destination
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant


compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_customer_wishlist_filters_serializes_and_mutates_packages():
    Base.metadata.create_all(bind=engine)
    db_session = SessionLocal()
    customer = Account(
        account_code="CUS-WISHLIST-API",
        name="Wishlist Customer",
        email="wishlist-customer@example.com",
        role=AccountRole.CUSTOMER,
        is_active=True,
    )
    destination = Destination(
        name="Himachal Pradesh",
        slug="himachal-pradesh",
        country="India",
        is_domestic=True,
    )
    db_session.add_all([customer, destination])
    db_session.flush()
    package = TourPackage(
        tour_code="TP-WISH-01",
        slug="himachal-summer-wishlist",
        title="Himachal Summer Escape",
        destination_id=destination.id,
        type="DOMESTIC",
        description="A summer tour.",
        is_featured=True,
    )
    db_session.add(package)
    db_session.flush()
    db_session.add(
        TourVariant(
            package_id=package.id,
            slug="himachal-summer-wishlist-variant",
            name="Summer",
            season_name="Summer Special",
            valid_from=date(2026, 4, 1),
            valid_to=date(2026, 6, 30),
            duration_days=5,
            duration_nights=4,
            list_price=2499,
            selling_price=2299,
            is_default=True,
            is_active=True,
        )
    )
    db_session.commit()
    db_session.refresh(customer)

    def override_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_customer] = lambda: customer
    try:
        with TestClient(app) as client:
            add_response = client.post("/api/v1/wishlist/himachal-summer-wishlist")
            assert add_response.status_code == 201

            duplicate_response = client.post("/api/v1/wishlist/himachal-summer-wishlist")
            assert duplicate_response.status_code == 409
            assert duplicate_response.json()["message"] == "Tour is already in your wishlist."

            list_response = client.get(
                "/api/v1/wishlist",
                params={"destination": "Himachal", "season": "Summer", "search": "Escape"},
            )
            assert list_response.status_code == 200
            body = list_response.json()
            assert body["pagination"]["total_items"] == 1
            assert body["data"][0]["destination"] == "Himachal Pradesh"
            assert body["data"][0]["season_name"] == "Summer Special"
            assert body["data"][0]["banner"] is None

            empty_response = client.get("/api/v1/wishlist", params={"destination": "Goa"})
            assert empty_response.status_code == 200
            assert empty_response.json()["pagination"]["total_items"] == 0

            remove_response = client.delete("/api/v1/wishlist/himachal-summer-wishlist")
            assert remove_response.status_code == 200
            missing_response = client.delete("/api/v1/wishlist/himachal-summer-wishlist")
            assert missing_response.status_code == 404
            assert missing_response.json()["message"] == "Tour is not in your wishlist."
    finally:
        app.dependency_overrides.clear()
        db_session.close()
        Base.metadata.drop_all(bind=engine)