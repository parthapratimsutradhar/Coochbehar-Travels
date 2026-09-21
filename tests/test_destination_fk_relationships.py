from app.models.destination import Destination
from app.models.enquiry import Enquiry
from app.models.hotel import Hotel


def test_destination_fk_columns_are_declared_on_models() -> None:
    assert "destination_id" in Enquiry.__table__.columns.keys()
    assert "destination_id" in Hotel.__table__.columns.keys()

    assert "enquiries" in Destination.__mapper__.relationships.keys()
    assert "hotels" in Destination.__mapper__.relationships.keys()
