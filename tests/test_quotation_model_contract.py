from app.models.quotation import Quotation


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
