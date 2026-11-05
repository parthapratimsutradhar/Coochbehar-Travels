from datetime import datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

from pypdf import PdfReader

from app.schemas.quotation import QuotationPdfResponse, QuotationResponse
from app.main import fastapi_app
from app.services.quotation_pdf_service import build_quotation_pdf


def test_quotation_response_schema_does_not_expose_hotels_or_vehicles():
    assert "hotels" not in QuotationResponse.model_fields
    assert "vehicles" not in QuotationResponse.model_fields
    assert "url" in QuotationPdfResponse.model_fields
    assert "path" in QuotationPdfResponse.model_fields


def test_quotation_pdf_openapi_schema_documents_response_fields():
    schema = fastapi_app.openapi()
    operation = schema["paths"]["/api/v1/admin/quotations/{quotation_id}/pdf"]["get"]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    response_name = response_ref.rsplit("/", 1)[-1]
    response_schema = schema["components"]["schemas"][response_name]
    data_ref = response_schema["properties"]["data"]["$ref"]
    pdf_response_name = data_ref.rsplit("/", 1)[-1]
    pdf_response_schema = schema["components"]["schemas"][pdf_response_name]

    assert set(pdf_response_schema["properties"]) == {"url", "path"}
    assert "hotel or vehicle details" in pdf_response_schema["properties"]["url"]["description"]
    assert "Hotel and vehicle details are excluded." in operation["description"]


def test_quotation_pdf_omits_hotel_and_vehicle_details_but_keeps_totals():
    quotation = SimpleNamespace(
        quotation_code="QT-PDF-001",
        tour_name="Sample Tour",
        travel_date=datetime(2026, 12, 1),
        return_date=datetime(2026, 12, 5),
        status="DRAFT",
        items=[
            SimpleNamespace(
                name="Hotel Room Package",
                description="Secret hotel details",
                quantity=1,
                unit_price=Decimal("100"),
                total_price=Decimal("100"),
                hotel=SimpleNamespace(
                    hotel_name="Hidden Hotel Name",
                    room_type="DELUXE",
                    check_in=datetime(2026, 12, 1),
                    check_out=datetime(2026, 12, 5),
                    room_count=1,
                    nights=4,
                ),
                vehicle=None,
            ),
            SimpleNamespace(
                name="Private Vehicle",
                description="Secret vehicle details",
                quantity=1,
                unit_price=Decimal("50"),
                total_price=Decimal("50"),
                hotel=None,
                vehicle=SimpleNamespace(
                    vehicle_name="Hidden Vehicle Name",
                    vehicle_type="SUV",
                    start_date=datetime(2026, 12, 1),
                    end_date=datetime(2026, 12, 5),
                    quantity=1,
                    rental_minutes=60,
                ),
            ),
            SimpleNamespace(
                name="Guide Service",
                description="Local guide",
                quantity=1,
                unit_price=Decimal("25"),
                total_price=Decimal("25"),
                hotel=None,
                vehicle=None,
            ),
        ],
        itinerary=[],
        subtotal=Decimal("175"),
        discount_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("175"),
        inclusion=None,
        exclusion=None,
        important_notes=None,
        terms_and_conditions=None,
    )

    pdf = build_quotation_pdf(quotation)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)

    assert "HOTEL ACCOMMODATION" not in text
    assert "TRANSPORTATION" not in text
    assert "Hidden Hotel Name" not in text
    assert "Hidden Vehicle Name" not in text
    assert "Hotel Room Package" not in text
    assert "Private Vehicle" not in text
    assert "Guide Service" in text
    assert "175" in text
