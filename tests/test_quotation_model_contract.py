from app.models.quotation import Quotation
from app.schemas.quotation import QuotationCreate


def test_quotation_model_uses_final_minimal_contract():
    assert hasattr(Quotation, "package_id")
    assert hasattr(Quotation, "variant_id")
    assert hasattr(Quotation, "destination_id")
    assert not hasattr(Quotation, "package")
    assert not hasattr(Quotation, "variant")
    assert not hasattr(Quotation, "offer")
    assert not hasattr(Quotation, "destination")
    assert not hasattr(Quotation, "hotel")
    assert not hasattr(Quotation, "room")
    assert not hasattr(Quotation, "vehicle")
    assert not hasattr(Quotation, "adult_count")
    assert not hasattr(Quotation, "child_count")
    assert not hasattr(Quotation, "senior_count")
    assert not hasattr(Quotation, "room_count")
    assert not hasattr(Quotation, "vehicle_count")
    assert not hasattr(Quotation, "meal_plan")


def test_draft_quotation_create_contract_allows_incomplete_details():
    payload = QuotationCreate.model_validate(
        {
            "enquiry_id": "4f58e4cc-5a4b-4a6d-a82f-c09f7baf6eb8",
            "save_as_draft": True,
        }
    )

    assert "status" not in QuotationCreate.model_fields
    assert payload.save_as_draft is True
    assert payload.tour_name is None
    assert payload.hotels is None
    assert payload.vehicles is None
