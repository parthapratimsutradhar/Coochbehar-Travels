from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.booking import Booking
from app.services.cdn_service import upload_content_to_cdn

LOGO_PATH = Path(__file__).resolve().parents[2] / "media" / "gantabyaa-logo.jpg"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_text(value)).replace("\n", "<br/>"), style)


def _date(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%d %b %Y")
    return _text(value)[:10]


def _money(value: Any) -> str:
    if value is None:
        return ""
    return f"{Decimal(str(value)):,.2f}"


def _number_words(number: int) -> str:
    units = (
        "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen",
    )
    tens = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")

    def under_thousand(value: int) -> str:
        words = []
        if value >= 1000:
            words.extend((under_thousand(value // 1000), "Thousand"))
            value %= 1000
        if value >= 100:
            words.extend((units[value // 100], "Hundred"))
            value %= 100
        if value >= 20:
            words.append(tens[value // 10])
            value %= 10
        if value:
            words.append(units[value])
        return " ".join(words)

    if number == 0:
        return units[0]
    parts = []
    for divisor, label in ((10000000, "Crore"), (100000, "Lakh"), (1000, "Thousand"), (1, "")):
        group, number = divmod(number, divisor)
        if group:
            parts.append(under_thousand(group))
            if label:
                parts.append(label)
    return " ".join(parts)


def _amount_in_words(value: Any) -> str:
    if value is None:
        return ""
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    result = f"{_number_words(rupees)} Rupees"
    if paise:
        result += f" and {_number_words(paise)} Paise"
    return result + " Only"


def _styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "VoucherTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#16324F"),
        fontSize=15,
        leading=18,
    )
    section = ParagraphStyle(
        "VoucherSection",
        parent=styles["Heading3"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#16324F"),
        spaceBefore=8,
        spaceAfter=4,
        fontSize=9,
        leading=11,
    )
    body = ParagraphStyle("VoucherBody", parent=styles["BodyText"], fontSize=8, leading=10)
    small = ParagraphStyle("VoucherSmall", parent=body, fontSize=7.5, leading=9)
    right = ParagraphStyle("VoucherRight", parent=body, alignment=TA_RIGHT)
    return styles, title, section, body, small, right


def _table(rows: list[list[Any]], widths: list[float], repeat_rows: int = 0) -> Table:
    return Table(rows, colWidths=widths, repeatRows=repeat_rows, style=TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAB7C4")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))


def _voucher_header(title: str, title_style: ParagraphStyle, body_style: ParagraphStyle) -> Table:
    logo = Image(str(LOGO_PATH), width=22 * mm, height=22 * mm, kind="proportional") if LOGO_PATH.is_file() else ""
    heading = [
        Paragraph("COOCHBEHAR TRAVELS", title_style),
        Paragraph("FIT / DOMESTIC / INTERNATIONAL / CAR RENTAL", body_style),
        Paragraph("Travel packages specialist", body_style),
    ]
    return Table(
        [[logo, heading], [Paragraph(title, title_style), ""]],
        colWidths=[30 * mm, 144 * mm],
        style=TableStyle([
            ("SPAN", (0, 1), (-1, 1)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 1), (-1, 1), 0.8, colors.HexColor("#16324F")),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
        ]),
    )


def _voucher_label_rows(
    pairs: list[tuple[str, Any]],
    label_style: ParagraphStyle,
    value_style: ParagraphStyle,
) -> list[list[Any]]:
    return [
        [_paragraph(label, label_style), _paragraph(value if value not in (None, "") else "-", value_style)]
        for label, value in pairs
    ]


def _party_count(booking: Booking) -> int:
    count = sum(
        getattr(booking, field, 0) or 0
        for field in ("adult_count", "child_count", "senior_count")
    )
    return count or len(getattr(booking, "travellers", []) or [])


def _guest_name(booking: Booking) -> str:
    customer = getattr(booking, "customer", None)
    if customer and getattr(customer, "name", None):
        return customer.name
    travellers = getattr(booking, "travellers", []) or []
    return getattr(travellers[0], "full_name", "") if travellers else ""


def _guest_contact(booking: Booking) -> str:
    customer = getattr(booking, "customer", None)
    if customer and getattr(customer, "mobile", None):
        return customer.mobile
    travellers = getattr(booking, "travellers", []) or []
    return getattr(travellers[0], "mobile", "") if travellers else ""


def _package_details(booking: Booking, voucher_type: str) -> str:
    booking_type = _text(getattr(booking, "booking_type", "")).replace("_", " ").title()
    package = getattr(booking, "package", None)
    package_name = getattr(package, "title", "") if package else ""
    voucher_label = "Car Rental" if voucher_type == "vehicle" else "FIT"
    details = [voucher_label, booking_type, package_name]
    return " / ".join(part for part in details if part)


def _hotel_items(booking: Booking) -> list[Any]:
    return [item for item in (getattr(booking, "trip_items", []) or []) if getattr(item, "hotel", None)]


def _vehicle_items(booking: Booking) -> list[Any]:
    return [item for item in (getattr(booking, "trip_items", []) or []) if getattr(item, "vehicle", None)]


def _voucher_balance(items: list[Any]) -> Decimal:
    return sum(
        (Decimal(str(getattr(item, "total_price", 0) or 0)) for item in items),
        Decimal(0),
    )


def _voucher_payer(booking: Booking, items: list[Any], field: str) -> str:
    payers = []
    traveller_name = _guest_name(booking)
    for item in items:
        detail = getattr(item, field)
        payer = traveller_name if getattr(detail, "paid_by_traveller", True) else "Company"
        if payer not in payers:
            payers.append(payer)
    return " / ".join(payers)


def _hotel_voucher_elements(
    booking: Booking,
    section: ParagraphStyle,
    body: ParagraphStyle,
    small: ParagraphStyle,
    standalone: bool = False,
) -> list[Any]:
    items = _hotel_items(booking)
    if not items:
        return []

    elements: list[Any] = []
    if standalone:
        _, title_style, _, body_style, _, _ = _styles()
        elements.extend([
            _voucher_header("FIT HOTEL CONFIRMATION VOUCHER", title_style, body_style),
            Spacer(1, 4 * mm),
        ])
    else:
        elements.append(Paragraph("FIT HOTEL CONFIRMATION VOUCHER", section))
    elements.extend([
        _table(
            _voucher_label_rows([
                ("Package details", _package_details(booking, "hotel")),
                ("Booking date", _date(getattr(booking, "created_at", None))),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
        Paragraph("TOURIST DETAILS", section),
        _table(
            _voucher_label_rows([
                ("Booking in the name of", _guest_name(booking)),
                ("Tourist contact number", _guest_contact(booking)),
                ("No. of persons", f"{_party_count(booking)} PAX"),
                ("Tour coordinator", getattr(getattr(booking, "sales_account", None), "name", "")),
                ("Coordinator contact", getattr(getattr(booking, "sales_account", None), "mobile", "")),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
    ])

    for index, item in enumerate(items, start=1):
        hotel = item.hotel
        master = getattr(hotel, "hotel", None)
        destination = getattr(master, "destination_ref", None) if master else None
        room_type = _text(getattr(hotel, "room_type", None)).replace("_", " ").title()
        room_details = f"{getattr(hotel, 'room_count', 1)} room(s)"
        if room_type:
            room_details += f" - {room_type}"
        elements.extend([
            Paragraph("HOTEL BOOKING DETAILS" if len(items) == 1 else f"HOTEL BOOKING DETAILS {index}", section),
            _table(
                [
                    [_paragraph("Hotel name", small), _paragraph(getattr(hotel, "hotel_name", "") or getattr(master, "name", ""), body)],
                    [_paragraph("Place", small), _paragraph(getattr(hotel, "place", None) or getattr(destination, "name", ""), body)],
                    [_paragraph("Address", small), _paragraph(getattr(hotel, "address", None) or getattr(master, "address", ""), body)],
                    [_paragraph("Check-in date", small), _paragraph(_date(getattr(hotel, "check_in", None)), body)],
                    [_paragraph("Check-out date", small), _paragraph(_date(getattr(hotel, "check_out", None)), body)],
                    [_paragraph("Room details", small), _paragraph(room_details, body)],
                    [_paragraph("Contact person", small), _paragraph(getattr(hotel, "contact_person", ""), body)],
                    [_paragraph("Contact number", small), _paragraph(getattr(hotel, "contact_number", ""), body)],
                    [_paragraph("Balance payment", small), _paragraph(f"Rs {_money(item.total_price)}/-", body)],
                ],
                [52 * mm, 122 * mm],
            ),
        ])

    amount = _voucher_balance(items)
    elements.extend([
        Paragraph("BALANCE PAYMENT DETAILS", section),
        _table(
            _voucher_label_rows([
                ("Balance payment", f"Rs {_money(amount)}/-" if amount is not None else ""),
                ("Balance payment in words", _amount_in_words(amount)),
                ("Balance payment to be paid by", _voucher_payer(booking, items, "hotel")),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
        Spacer(1, 9 * mm),
        _signature_table(small),
    ])
    return elements


def _vehicle_voucher_elements(
    booking: Booking,
    section: ParagraphStyle,
    body: ParagraphStyle,
    small: ParagraphStyle,
    standalone: bool = False,
) -> list[Any]:
    items = _vehicle_items(booking)
    if not items:
        return []

    elements: list[Any] = []
    if standalone:
        _, title_style, _, body_style, _, _ = _styles()
        elements.extend([
            _voucher_header("FIT VEHICLE CONFIRMATION VOUCHER", title_style, body_style),
            Spacer(1, 4 * mm),
        ])
    else:
        elements.append(Paragraph("FIT VEHICLE CONFIRMATION VOUCHER", section))
    coordinator = getattr(booking, "sales_account", None)
    elements.extend([
        _table(
            _voucher_label_rows([
                ("Package details", _package_details(booking, "vehicle")),
                ("Booking date", _date(getattr(booking, "created_at", None))),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
        Paragraph("TOURIST DETAILS", section),
        _table(
            _voucher_label_rows([
                ("Booking in the name of", _guest_name(booking)),
                ("Tourist contact number", _guest_contact(booking)),
                ("No. of persons", f"{_party_count(booking)} PAX"),
                ("Tour coordinator", getattr(coordinator, "name", "")),
                ("Coordinator contact", getattr(coordinator, "mobile", "")),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
    ])
    for index, item in enumerate(items, start=1):
        vehicle = item.vehicle
        master = getattr(vehicle, "vehicle", None)
        vehicle_name = getattr(vehicle, "vehicle_name", "") or getattr(master, "name", "")
        vehicle_type = _text(getattr(vehicle, "vehicle_type", None) or getattr(master, "vehicle_type", None))
        elements.extend([
            Paragraph("BOOKING DETAILS" if len(items) == 1 else f"BOOKING DETAILS {index}", section),
            _table(
                [
                    [_paragraph("Pick up", small), _paragraph(getattr(vehicle, "pickup_location", ""), body), _paragraph("Pick up date", small), _paragraph(_date(getattr(vehicle, "start_date", None)), body)],
                    [_paragraph("Drop at", small), _paragraph(getattr(vehicle, "drop_location", ""), body), _paragraph("Drop date", small), _paragraph(_date(getattr(vehicle, "end_date", None)), body)],
                    [_paragraph("Vehicle owner", small), _paragraph(getattr(vehicle, "owner_name", ""), body), _paragraph("Owner contact", small), _paragraph(getattr(vehicle, "owner_contact", ""), body)],
                    [_paragraph("Driver name", small), _paragraph(getattr(vehicle, "driver_name", ""), body), _paragraph("Driver contact", small), _paragraph(getattr(vehicle, "driver_contact", ""), body)],
                    [_paragraph("Vehicle", small), _paragraph(vehicle_name, body), _paragraph("Vehicle type", small), _paragraph(vehicle_type, body)],
                    [_paragraph("Car number", small), _paragraph(getattr(vehicle, "registration_number", None) or getattr(master, "registration_number", ""), body), "", ""],
                    [_paragraph("Balance payment", small), _paragraph(f"Rs {_money(item.total_price)}/-", body), "", ""],
                ],
                [36 * mm, 51 * mm, 36 * mm, 51 * mm],
            ),
        ])
    itinerary = getattr(booking, "trip_itinerary", []) or []
    if itinerary:
        itinerary_rows = [[_paragraph("Day", small), _paragraph("Date", small), _paragraph("Plan", small)]]
        for day in itinerary:
            plan = _text(getattr(day, "title", ""))
            description = _text(getattr(day, "description", ""))
            if description:
                plan = f"{plan}\n{description}"
            itinerary_rows.append([
                _paragraph(getattr(day, "day_number", ""), small),
                _paragraph(_date(getattr(day, "date", None)), small),
                _paragraph(plan, small),
            ])
        elements.extend([
            Paragraph("PLANNED ITINERARY", section),
            _table(itinerary_rows, [18 * mm, 35 * mm, 121 * mm], repeat_rows=1),
        ])

    amount = _voucher_balance(items)
    elements.extend([
        Paragraph("PAYMENT DETAILS", section),
        _table(
            _voucher_label_rows([
                ("Balance payment", f"Rs {_money(amount)}/-" if amount is not None else ""),
                ("Balance payment in words", _amount_in_words(amount)),
                ("Payment to be released by", _voucher_payer(booking, items, "vehicle")),
            ], small, body),
            [52 * mm, 122 * mm],
        ),
        Spacer(1, 9 * mm),
        _signature_table(small),
    ])
    return elements


def _signature_table(style: ParagraphStyle) -> Table:
    return Table(
        [[_paragraph("SIGNATURE OF CUSTOMER", style), _paragraph("SIGNATURE OF AUTHORITY", style)]],
        colWidths=[87 * mm, 87 * mm],
        style=TableStyle([
            ("LINEABOVE", (0, 0), (0, 0), 0.6, colors.HexColor("#16324F")),
            ("LINEABOVE", (1, 0), (1, 0), 0.6, colors.HexColor("#16324F")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]),
    )


def build_booking_voucher_pdf(booking: Booking, voucher_type: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=f"{voucher_type.title()} voucher {booking.booking_code}",
        author="Coochbehar Travels",
    )
    _, _, section, body, small, _ = _styles()
    if voucher_type == "hotel":
        story = _hotel_voucher_elements(booking, section, body, small, standalone=True)
    elif voucher_type == "vehicle":
        story = _vehicle_voucher_elements(booking, section, body, small, standalone=True)
    else:
        raise ValueError(f"Unsupported booking voucher type: {voucher_type}")
    if not story:
        raise ValueError(f"No {voucher_type} voucher details found for this booking.")
    document.build(story)
    return buffer.getvalue()


def build_booking_pdf(booking: Booking) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Booking {booking.booking_code}",
        author="Coochbehar Travels",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("BookingTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#16324F"))
    section = ParagraphStyle("Section", parent=styles["Heading2"], textColor=colors.HexColor("#16324F"), spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle("Body", parent=styles["BodyText"], leading=14)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11)
    amount = ParagraphStyle("Amount", parent=body, alignment=TA_RIGHT)

    story = [
        Paragraph("COOCHBEHAR TRAVELS", title),
        Paragraph("BOOKING CONFIRMATION", styles["Heading3"]),
        Spacer(1, 5 * mm),
        Table([
            [Paragraph("Booking", body), Paragraph(_text(booking.booking_code), body)],
            [Paragraph("Customer", body), Paragraph(_text(booking.customer.name if booking.customer else ""), body)],
            [Paragraph("Package", body), Paragraph(_text(booking.package.title if booking.package else booking.booking_type), body)],
            [Paragraph("Status", body), Paragraph(_text(booking.status), body)],
        ], colWidths=[38 * mm, 136 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F7")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])),
        Paragraph("TRAVELLERS", section),
    ]

    traveller_rows = [[Paragraph("Name", small), Paragraph("Mobile", small), Paragraph("Email", small)]]
    for traveller in booking.travellers:
        traveller_rows.append([
            Paragraph(_text(traveller.full_name), small),
            Paragraph(_text(traveller.mobile), small),
            Paragraph(_text(traveller.email), small),
        ])
    if len(traveller_rows) == 1:
        traveller_rows.append([Paragraph("No traveller details supplied", small), "", ""])
    story.append(Table(traveller_rows, colWidths=[62 * mm, 44 * mm, 62 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ])))

    story.append(Paragraph("ITINERARY", section))
    itinerary_rows = [[Paragraph("Day", small), Paragraph("Date", small), Paragraph("Plan", small), Paragraph("Overnight", small)]]
    for day in booking.trip_itinerary:
        itinerary_rows.append([
            Paragraph(_text(day.day_number), small),
            Paragraph(_text(day.date)[:10], small),
            Paragraph(f"<b>{_text(day.title)}</b><br/>{_text(day.description)}", small),
            Paragraph(_text(day.overnight_location), small),
        ])
    if len(itinerary_rows) == 1:
        itinerary_rows.append([Paragraph("No itinerary supplied", small), "", "", ""])
    story.append(Table(itinerary_rows, colWidths=[12 * mm, 28 * mm, 92 * mm, 42 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ])))

    story.append(Paragraph("BOOKING COSTS", section))
    cost_rows = [[Paragraph("Particulars", small), Paragraph("Quantity", small), Paragraph("Unit price", small), Paragraph("Total", small)]]
    for item in booking.trip_items:
        cost_rows.append([
            Paragraph(f"<b>{_text(item.name)}</b><br/>{_text(item.description)}", small),
            Paragraph(_text(item.quantity), small),
            Paragraph(_text(item.unit_price), amount),
            Paragraph(_text(item.total_price), amount),
        ])
    cost_rows.extend([
        [Paragraph("Subtotal", body), "", "", Paragraph(_text(booking.subtotal), amount)],
        [Paragraph("Discount", body), "", "", Paragraph(_text(booking.discount_amount), amount)],
        [Paragraph("TOTAL", body), "", "", Paragraph(f"<b>{_text(booking.total_amount)}</b>", amount)],
    ])
    story.append(Table(cost_rows, colWidths=[92 * mm, 20 * mm, 30 * mm, 32 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF1F7")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ])))
    for voucher_elements in (
        _hotel_voucher_elements(booking, section, body, small),
        _vehicle_voucher_elements(booking, section, body, small),
    ):
        if voucher_elements:
            story.extend([PageBreak(), *voucher_elements])
    document.build(story)
    return buffer.getvalue()


async def generate_and_upload_booking_pdf(booking: Booking) -> dict[str, Any]:
    return await upload_content_to_cdn(
        content=build_booking_pdf(booking),
        filename=f"{booking.booking_code}.pdf",
        content_type="application/pdf",
        target_folder="temporary-uploads",
    )
