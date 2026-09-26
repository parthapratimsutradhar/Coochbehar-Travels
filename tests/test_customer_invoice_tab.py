import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.core.enums import BookingStatus, CostItemType
from app.services.customer_service import CustomerService


def test_customer_invoice_tab_groups_cost_breakdown_by_booking():
    customer_id = uuid.uuid4()
    bookings = [
        SimpleNamespace(
            id=uuid.uuid4(),
            booking_code="BK-001",
            package=SimpleNamespace(title="Coastal Tour"),
            status=BookingStatus.CONFIRMED,
            adult_count=2,
            child_count=1,
            senior_count=0,
            trip_items=[
                SimpleNamespace(
                    id=uuid.uuid4(),
                    item_type=CostItemType.TRANSPORT,
                    name="Airport transfer",
                    description=None,
                    quantity=1,
                    unit_price=Decimal("1500.00"),
                    total_price=Decimal("1500.00"),
                )
            ],
            subtotal=Decimal("10000.00"),
            discount_amount=Decimal("500.00"),
            total_amount=Decimal("9500.00"),
            paid_amount=Decimal("3000.00"),
            due_amount=Decimal("6500.00"),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            booking_code="BK-002",
            package=None,
            status=BookingStatus.PARTIALLY_PAID,
            adult_count=1,
            child_count=0,
            senior_count=0,
            trip_items=[],
            subtotal=Decimal("4000.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("4000.00"),
            paid_amount=Decimal("1000.00"),
            due_amount=Decimal("3000.00"),
        ),
    ]

    class BookingRepositoryStub:
        def list_all(self, *, page, page_size, customer_id):
            assert customer_id == expected_customer_id
            return bookings, len(bookings)

    expected_customer_id = customer_id
    service = CustomerService(None)
    service.booking_repo = BookingRepositoryStub()

    payload = service.get_customer_tab_data(
        customer_id=customer_id,
        customer=SimpleNamespace(),
        tab="invoice",
        page=1,
        page_size=10,
    )

    assert payload["tab"] == "invoice"
    assert [item["booking_code"] for item in payload["items"]] == ["BK-001", "BK-002"]
    first_breakdown = payload["items"][0]["cost_breakdown"]
    assert first_breakdown["items"][0]["name"] == "Airport transfer"
    assert first_breakdown["subtotal"] == "10000.00"
    assert first_breakdown["discount_amount"] == "500.00"
    assert first_breakdown["total_amount"] == "9500.00"
    assert first_breakdown["paid_amount"] == "3000.00"
    assert first_breakdown["due_amount"] == "6500.00"
    assert payload["items"][1]["cost_breakdown"]["items"] == []