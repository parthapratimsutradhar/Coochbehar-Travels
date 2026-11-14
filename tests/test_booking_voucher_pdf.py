from datetime import datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pypdf import PdfReader

from app.core.enums import CostItemType
from app.services.booking_pdf_service import build_booking_pdf, build_booking_voucher_pdf
from app.services.booking_service import BookingService
from app.services.quotation_service import QuotationService


def _pdf_text(content: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)


def _booking():
    hotel = SimpleNamespace(
        hotel_name="Hotel Jagdamba",
        place="Katra",
        address="Railway Road, Katra",
        contact_person="Front Desk",
        contact_number="+91 95967 08401",
        check_in=datetime(2026, 12, 1),
        check_out=datetime(2026, 12, 3),
        room_count=2,
        room_type="DELUXE",
        paid_by_traveller=False,
        hotel=None,
    )
    vehicle = SimpleNamespace(
        vehicle_name="Innova",
        vehicle_type="SUV",
        pickup_location="Srinagar Railway Station",
        drop_location="Srinagar Railway Station",
        start_date=datetime(2026, 12, 1),
        end_date=datetime(2026, 12, 3),
        owner_name="Vehicle Owner",
        owner_contact="+91 90000 00000",
        driver_name="Driver",
        driver_contact="+91 91111 11111",
        registration_number="WB01A1234",
        paid_by_traveller=True,
        vehicle=None,
    )
    itinerary = SimpleNamespace(
        day_number=1,
        date=datetime(2026, 12, 1),
        title="Srinagar local sightseeing",
        description="Visit the local gardens.",
        overnight_location="Srinagar",
    )
    return SimpleNamespace(
        booking_code="BK-VOUCHER-001",
        customer=SimpleNamespace(name="Amit Guest", mobile="+91 98888 88888"),
        sales_account=SimpleNamespace(name="Tour Coordinator", mobile="+91 97777 77777"),
        adult_count=2,
        child_count=1,
        senior_count=0,
        travellers=[],
        trip_items=[
            SimpleNamespace(
                hotel=hotel,
                vehicle=None,
                name="Hotel",
                description=None,
                quantity=1,
                unit_price=Decimal("100"),
                total_price=Decimal("3400"),
            ),
            SimpleNamespace(
                hotel=None,
                vehicle=vehicle,
                name="Vehicle",
                description=None,
                quantity=1,
                unit_price=Decimal("100"),
                total_price=Decimal("18000"),
            ),
        ],
        trip_itinerary=[itinerary],
        due_amount=Decimal("18000.00"),
        subtotal=Decimal("20000.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("20000.00"),
        package=None,
        booking_type="DOMESTIC",
        status="CONFIRMED",
    )


def test_standalone_hotel_voucher_contains_hotel_and_payment_details():
    text = _pdf_text(build_booking_voucher_pdf(_booking(), "hotel"))

    assert "FIT HOTEL CONFIRMATION VOUCHER" in text
    assert "Amit Guest" in text
    assert "Hotel Jagdamba" in text
    assert "Railway Road, Katra" in text
    assert "01 Dec 2026" in text
    assert "Three Thousand Four Hundred Rupees Only" in text
    assert "Company" in text
    assert "Tour Coordinator" in text


def test_voucher_balance_uses_its_trip_item_amount():
    booking = _booking()
    hotel_item = booking.trip_items[0]
    hotel_item.total_price = Decimal("3600.00")

    text = _pdf_text(build_booking_voucher_pdf(booking, "hotel"))

    assert "Three Thousand Six Hundred Rupees Only" in text


def test_standalone_vehicle_voucher_contains_driver_vehicle_and_itinerary_details():
    text = _pdf_text(build_booking_voucher_pdf(_booking(), "vehicle"))

    assert "FIT VEHICLE CONFIRMATION VOUCHER" in text
    assert "Srinagar Railway Station" in text
    assert "Vehicle Owner" in text
    assert "Driver" in text
    assert "WB01A1234" in text
    assert "Srinagar local sightseeing" in text
    assert "Eighteen Thousand Rupees Only" in text


def test_booking_pdf_includes_available_separate_voucher_sections():
    text = _pdf_text(build_booking_pdf(_booking()))

    assert "FIT HOTEL CONFIRMATION VOUCHER" in text
    assert "FIT VEHICLE CONFIRMATION VOUCHER" in text


def test_booking_voucher_download_returns_not_found_when_type_is_missing():
    booking = _booking()
    booking.trip_items = [SimpleNamespace(hotel=None, vehicle=None)]
    service = BookingService(db=None)
    service.get_booking = lambda booking_id: booking

    with pytest.raises(HTTPException) as error:
        service.render_booking_voucher_pdf("booking-id", "hotel")

    assert error.value.status_code == 404


def test_quotation_conversion_preserves_voucher_details():
    hotel = SimpleNamespace(
        hotel_id=None,
        hotel_name="Hotel Jagdamba",
        check_in=datetime(2026, 12, 1),
        check_out=datetime(2026, 12, 3),
        nights=2,
        room_count=1,
        room_type="DELUXE",
        place="Katra",
        address="Railway Road",
        contact_person="Front Desk",
        contact_number="+91 95967 08401",
        paid_by_traveller=False,
    )
    vehicle = SimpleNamespace(
        vehicle_id=None,
        vehicle_name="Innova",
        vehicle_type="SUV",
        start_date=datetime(2026, 12, 1),
        end_date=datetime(2026, 12, 3),
        rental_minutes=60,
        quantity=1,
        pickup_location="Srinagar Station",
        drop_location="Srinagar Station",
        owner_name="Vehicle Owner",
        owner_contact="+91 90000 00000",
        driver_name="Driver",
        driver_contact="+91 91111 11111",
        registration_number="WB01A1234",
        paid_by_traveller=True,
    )
    hotel_item = SimpleNamespace(
        item_type=CostItemType.HOTEL,
        name="Hotel",
        description=None,
        quantity=1,
        unit_price=Decimal("100"),
        total_price=Decimal("100"),
        hotel=hotel,
        vehicle=None,
    )
    vehicle_item = SimpleNamespace(
        item_type=CostItemType.TRANSPORT,
        name="Vehicle",
        description=None,
        quantity=1,
        unit_price=Decimal("100"),
        total_price=Decimal("100"),
        hotel=None,
        vehicle=vehicle,
    )
    itinerary_day = SimpleNamespace(
        day_number=1,
        date=datetime(2026, 12, 1),
        title="Srinagar",
        description="Local sightseeing",
        overnight_location="Srinagar",
        meal_plan=None,
        sort_order=0,
    )
    quotation = SimpleNamespace(
        id="quotation-id",
        customer_id="customer-id",
        enquiry_id="enquiry-id",
        package_id=None,
        variant_id=None,
        departure_id="departure-id",
        subtotal=Decimal("200"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("200"),
        items=[hotel_item, vehicle_item],
        itinerary=[itinerary_day],
    )
    service = QuotationService(db=SimpleNamespace(commit=lambda: None, refresh=lambda _: None))
    expected_booking = SimpleNamespace(id="booking-id")

    with (
        patch("app.repository.booking_repo.BookingRepository.create", return_value=expected_booking) as create_booking,
        patch("app.services.tour_points_service.TourPointsService.award_booking_points"),
    ):
        result = service._create_booking_from_quotation(quotation, {}, travellers=[])

    assert result is expected_booking
    _, kwargs = create_booking.call_args
    assert kwargs["hotels"][0]["contact_person"] == "Front Desk"
    assert kwargs["hotels"][0]["paid_by_traveller"] is False
    assert kwargs["vehicles"][0]["driver_name"] == "Driver"
    assert kwargs["vehicles"][0]["registration_number"] == "WB01A1234"
    assert kwargs["vehicles"][0]["paid_by_traveller"] is True
    assert kwargs["itinerary"][0]["title"] == "Srinagar"
