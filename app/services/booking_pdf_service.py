from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.booking import Booking
from app.services.cloudinary_service import upload_content_to_cloudinary


def _text(value: Any) -> str:
    return str(value) if value is not None else ""


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

    traveller_rows = [[Paragraph("Name", small), Paragraph("Type", small), Paragraph("Mobile", small), Paragraph("Email", small)]]
    for traveller in booking.travellers:
        traveller_rows.append([
            Paragraph(_text(traveller.full_name), small),
            Paragraph(_text(getattr(traveller, "traveler_type", "")), small),
            Paragraph(_text(traveller.mobile), small),
            Paragraph(_text(traveller.email), small),
        ])
    if len(traveller_rows) == 1:
        traveller_rows.append([Paragraph("No traveller details supplied", small), "", "", ""])
    story.append(Table(traveller_rows, colWidths=[52 * mm, 28 * mm, 38 * mm, 56 * mm], repeatRows=1, style=TableStyle([
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
    document.build(story)
    return buffer.getvalue()


async def generate_and_upload_booking_pdf(booking: Booking) -> dict[str, Any]:
    return await upload_content_to_cloudinary(
        content=build_booking_pdf(booking),
        filename=f"{booking.booking_code}.pdf",
        content_type="application/pdf",
        sub_folder="temporary-uploads/bookings",
    )
