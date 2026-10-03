import asyncio
import sys
import uuid
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

from fastapi import Request


def test_visitor_realtime_events_are_exposed():
    from app.realtime.socket_manager import REALTIME_EVENTS

    expected = {
        "visitor_connected",
        "visitor_disconnected",
        "page_view",
        "page_navigation",
        "activity",
        "click",
        "session_updated",
        "visitor_identified",
        "visitor_location_updated",
    }

    assert expected.issubset(REALTIME_EVENTS)


def test_identify_visitor_fills_missing_location_from_request_ip(monkeypatch):
    from app.api.v1.enduser import visitors as visitor_api
    from app.schemas.visitor import VisitorIdentifyRequest

    captured = {}
    now = datetime.now(timezone.utc)
    visitor = SimpleNamespace(
        id=uuid.uuid4(),
        visitor_code="VIS-LOCATION",
        fingerprint="fingerprint-1",
        ip_address="8.8.8.8",
        country="India",
        state="West Bengal",
        city="Kolkata",
        browser="test-agent",
        os=None,
        device=None,
        customer_id=None,
        first_seen=now,
        last_seen=now,
    )

    class FakeTrackingService:
        def __init__(self, db):
            pass

        def identify_visitor(self, **kwargs):
            captured.update(kwargs)
            return visitor, True

    async def fake_lookup(ip_address):
        assert ip_address == "8.8.8.8"
        return {"country": "India", "state": "West Bengal", "city": "Kolkata"}

    monkeypatch.setattr(visitor_api, "TrackingService", FakeTrackingService)
    monkeypatch.setattr(visitor_api, "lookup_ip_location", fake_lookup)
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/visitors/identify",
            "raw_path": b"/api/v1/visitors/identify",
            "query_string": b"",
            "headers": [(b"user-agent", b"test-agent")],
            "client": ("8.8.8.8", 12345),
            "server": ("testserver", 80),
        }
    )

    response = asyncio.run(
        visitor_api.identify_visitor(
            VisitorIdentifyRequest(fingerprint="fingerprint-1"),
            request,
            db=None,
            current_customer=None,
        )
    )

    assert captured["ip_address"] == "8.8.8.8"
    assert captured["country"] == "India"
    assert captured["state"] == "West Bengal"
    assert captured["city"] == "Kolkata"
    assert captured["customer_id"] is None
    assert response.data.visitor.city == "Kolkata"

    customer_id = uuid.uuid4()
    asyncio.run(
        visitor_api.identify_visitor(
            VisitorIdentifyRequest(fingerprint="fingerprint-1"),
            request,
            db=None,
            current_customer=SimpleNamespace(id=customer_id),
        )
    )
    assert captured["customer_id"] == customer_id


def test_ip_geolocation_skips_private_addresses():
    from app.services.ip_geolocation_service import lookup_ip_location

    assert asyncio.run(lookup_ip_location("127.0.0.1")) == {}
    assert asyncio.run(lookup_ip_location("192.168.1.10")) == {}


def test_ip_geolocation_maps_local_city_database_fields(monkeypatch):
    from app.services import ip_geolocation_service

    result = SimpleNamespace(
        country=SimpleNamespace(name="India"),
        subdivisions=SimpleNamespace(most_specific=SimpleNamespace(name="West Bengal")),
        city=SimpleNamespace(name="Kolkata"),
    )

    class FakeReader:
        def city(self, ip_address):
            assert ip_address == "8.8.8.8"
            return result

    monkeypatch.setattr(ip_geolocation_service, "_get_reader", lambda: FakeReader())

    assert ip_geolocation_service._lookup_city("8.8.8.8") == {
        "country": "India",
        "state": "West Bengal",
        "city": "Kolkata",
    }


def test_ip_geolocation_opens_configured_local_database(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services import ip_geolocation_service

    database_path = tmp_path / "GeoLite2-City.mmdb"
    database_path.write_bytes(b"test database")
    location = SimpleNamespace(
        country=SimpleNamespace(name="India"),
        subdivisions=SimpleNamespace(most_specific=SimpleNamespace(name="West Bengal")),
        city=SimpleNamespace(name="Kolkata"),
    )

    class FakeReader:
        def __init__(self, path):
            assert path == str(database_path)

        def city(self, ip_address):
            assert ip_address == "1.1.1.1"
            return location

        def close(self):
            pass

    monkeypatch.setattr(settings, "GEOLITE2_CITY_DB_PATH", str(database_path))
    geoip2_module = ModuleType("geoip2")
    database_module = ModuleType("geoip2.database")
    database_module.Reader = FakeReader
    geoip2_module.database = database_module
    monkeypatch.setitem(sys.modules, "geoip2", geoip2_module)
    monkeypatch.setitem(sys.modules, "geoip2.database", database_module)
    monkeypatch.setattr(ip_geolocation_service, "_reader", None)
    monkeypatch.setattr(ip_geolocation_service, "_reader_path", None)
    ip_geolocation_service._location_cache.pop("1.1.1.1", None)

    assert asyncio.run(ip_geolocation_service.lookup_ip_location("1.1.1.1")) == {
        "country": "India",
        "state": "West Bengal",
        "city": "Kolkata",
    }


def test_ip_geolocation_without_local_database_returns_empty(monkeypatch, tmp_path):
    from app.core.config import settings
    from app.services.ip_geolocation_service import lookup_ip_location

    monkeypatch.setattr(settings, "GEOLITE2_CITY_DB_PATH", str(tmp_path / "missing.mmdb"))

    assert asyncio.run(lookup_ip_location("8.8.4.4")) == {}


def test_customer_presence_payload_includes_database_customer_fields(monkeypatch):
    from app.realtime import presence, socket_manager

    active_visitors = {}
    monkeypatch.setattr(presence, "ACTIVE_VISITORS", active_visitors)
    monkeypatch.setattr(socket_manager, "ACTIVE_VISITORS", active_visitors)
    visitor_id = str(uuid.uuid4())
    presence.upsert_active_visitor(
        visitor_id=visitor_id,
        customer_id=str(uuid.uuid4()),
        visitor_type="customer",
        customer_name="Partha",
        customer_email="partha@example.com",
        customer_mobile="+919000000001",
        customer_profile_pic="profile-picture/partha.jpg",
        is_anonymous=False,
    )

    payload = socket_manager._build_visitor_payload(visitor_id)

    assert payload["customer_name"] == "Partha"
    assert payload["customer_email"] == "partha@example.com"
    assert payload["customer_mobile"] == "+919000000001"
    assert payload["customer_profile_pic"] == "profile-picture/partha.jpg"


def test_visitor_identified_broadcast_includes_linked_customer_data(monkeypatch):
    from app.services import socket_service

    customer = SimpleNamespace(
        role="CUSTOMER",
        name="Partha",
        email="partha@example.com",
        mobile="+919000000001",
        profile_pic="profile-picture/partha.jpg",
    )
    visitor = SimpleNamespace(
        id=uuid.uuid4(),
        visitor_code="VIS-CUSTOMER",
        fingerprint="fingerprint-customer",
        ip_address="8.8.8.8",
        country="India",
        state="West Bengal",
        city="Kolkata",
        browser="test-agent",
        os=None,
        device=None,
        customer_id=uuid.uuid4(),
        customer=customer,
        first_seen=datetime.now(timezone.utc),
    )
    broadcasts = []
    monkeypatch.setattr(
        socket_service,
        "_safe_broadcast",
        lambda event_names, payload, rooms: broadcasts.append(payload),
    )

    socket_service.emit_visitor_identified(visitor, is_new=False)

    assert broadcasts[0]["customer_name"] == "Partha"
    assert broadcasts[0]["customer_email"] == "partha@example.com"
    assert broadcasts[0]["customer_mobile"] == "+919000000001"
    assert broadcasts[0]["state"] == "West Bengal"


def test_customer_identification_updates_active_presence_immediately(monkeypatch):
    from app.realtime import presence
    from app.services import socket_service

    customer = SimpleNamespace(
        role="CUSTOMER",
        name="Partha",
        email="partha@example.com",
        mobile="+919000000001",
        profile_pic=None,
    )
    visitor_id = uuid.uuid4()
    visitor = SimpleNamespace(
        id=visitor_id,
        visitor_code="VIS-LIVE-CUSTOMER",
        fingerprint="fingerprint-live-customer",
        ip_address="8.8.8.8",
        country="India",
        state="West Bengal",
        city="Kolkata",
        browser="Chrome",
        os="Windows",
        device="desktop",
        customer_id=uuid.uuid4(),
        customer=customer,
        first_seen=datetime.now(timezone.utc),
    )
    active_visitors = {str(visitor_id): {"visitor_id": str(visitor_id), "page": "/tours"}}
    broadcasts = []
    monkeypatch.setattr(presence, "ACTIVE_VISITORS", active_visitors)
    monkeypatch.setattr(socket_service, "ACTIVE_VISITORS", active_visitors)
    monkeypatch.setattr(
        socket_service,
        "_safe_broadcast",
        lambda event_names, payload, rooms: broadcasts.append((event_names, payload)),
    )

    socket_service.emit_visitor_identified(visitor, is_new=False)

    live_presence = active_visitors[str(visitor_id)]
    assert live_presence["visitor_type"] == "customer"
    assert live_presence["customer_name"] == "Partha"
    assert live_presence["customer_email"] == "partha@example.com"
    assert live_presence["is_anonymous"] is False
    assert any("visitor_identified" in names for names, _ in broadcasts)
    live_stats = next(payload for names, payload in broadcasts if "live_stats" in names)
    assert live_stats["customers"] == 1
    assert live_stats["visitors"] == 0


def test_live_stats_snapshots_are_targeted_and_updates_are_compact(monkeypatch):
    from app.realtime import socket_manager

    emitted = []

    async def fake_emit(event, payload, *, room):
        emitted.append((event, payload, room))

    monkeypatch.setattr(
        socket_manager,
        "sio",
        SimpleNamespace(emit=fake_emit),
    )
    monkeypatch.setattr(
        socket_manager,
        "ACTIVE_VISITORS",
        {"visitor-1": {"visitor_id": "visitor-1"}},
    )
    monkeypatch.setattr(
        socket_manager,
        "get_live_counts",
        lambda: {"total": 1, "customers": 0, "visitors": 1},
    )

    asyncio.run(socket_manager._broadcast_live_stats(sid="admin-sid"))
    asyncio.run(socket_manager._broadcast_live_stats(include_visitors=False))
    asyncio.run(socket_manager._broadcast("visitor_connected", {"visitor_id": "visitor-1"}))

    assert emitted[0][2] == "admin-sid"
    assert emitted[0][1]["active_visitors"] == [{"visitor_id": "visitor-1"}]
    assert emitted[1][2] == "ADMIN"
    assert "active_visitors" not in emitted[1][1]
    assert len(emitted) == 3
    assert emitted[2][2] == "ADMIN"
