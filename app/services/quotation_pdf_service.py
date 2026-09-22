from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.quotation import Quotation
from app.services.cloudinary_service import upload_content_to_cloudinary


def _text(value: Any) -> str:
    return str(value) if value is not None else ""


def build_quotation_pdf(quotation: Quotation) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Quotation {quotation.quotation_code}",
        author="Coochbehar Travels",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("QuotationTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#16324F"))
    section = ParagraphStyle("Section", parent=styles["Heading2"], textColor=colors.HexColor("#16324F"), spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle("Body", parent=styles["BodyText"], leading=14)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11)
    amount = ParagraphStyle("Amount", parent=body, alignment=TA_RIGHT)

    story = [
        Paragraph("COOCHBEHAR TRAVELS", title),
        Paragraph("Luxury Stay & Sightseeing Package", styles["Heading3"]),
        Spacer(1, 5 * mm),
        Table(
            [
                [Paragraph("Quotation", body), Paragraph(_text(quotation.quotation_code), body)],
                [Paragraph("Tour", body), Paragraph(_text(quotation.tour_name), body)],
                [Paragraph("Travel dates", body), Paragraph(f"{_text(quotation.travel_date)} to {_text(quotation.return_date)}", body)],
                [Paragraph("Status", body), Paragraph(_text(quotation.status), body)],
            ],
            colWidths=[38 * mm, 136 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F7")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
    ]

    hotel_items = [item for item in quotation.items if item.hotel]
    if hotel_items:
        story.append(Paragraph("HOTEL ACCOMMODATION", section))
        hotel_rows = [[
            Paragraph("Hotel", small),
            Paragraph("Check-in", small),
            Paragraph("Check-out", small),
            Paragraph("Room", small),
            Paragraph("Nights", small),
            Paragraph("Cost", small),
        ]]
        for item in hotel_items:
            hotel = item.hotel
            hotel_rows.append([
                Paragraph(f"<b>{_text(hotel.hotel_name)}</b><br/>{_text(hotel.room_type)}", small),
                Paragraph(_text(hotel.check_in)[:10], small),
                Paragraph(_text(hotel.check_out)[:10], small),
                Paragraph(_text(hotel.room_count), small),
                Paragraph(_text(hotel.nights), small),
                Paragraph(_text(item.total_price), amount),
            ])
        story.append(Table(hotel_rows, colWidths=[52 * mm, 25 * mm, 25 * mm, 18 * mm, 18 * mm, 36 * mm], repeatRows=1, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])))

    vehicle_items = [item for item in quotation.items if item.vehicle]
    if vehicle_items:
        story.append(Paragraph("TRANSPORTATION", section))
        vehicle_rows = [[
            Paragraph("Vehicle", small),
            Paragraph("Start", small),
            Paragraph("End", small),
            Paragraph("Quantity", small),
            Paragraph("Service", small),
            Paragraph("Cost", small),
        ]]
        for item in vehicle_items:
            vehicle = item.vehicle
            vehicle_rows.append([
                Paragraph(f"<b>{_text(vehicle.vehicle_name)}</b><br/>{_text(vehicle.vehicle_type)}", small),
                Paragraph(_text(vehicle.start_date)[:10], small),
                Paragraph(_text(vehicle.end_date)[:10], small),
                Paragraph(_text(vehicle.quantity), small),
                Paragraph(f"{_text(vehicle.rental_minutes)} minutes", small),
                Paragraph(_text(item.total_price), amount),
            ])
        story.append(Table(vehicle_rows, colWidths=[52 * mm, 25 * mm, 25 * mm, 20 * mm, 30 * mm, 22 * mm], repeatRows=1, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])))

    story.append(Paragraph("ITINERARY", section))

    itinerary_rows = [[Paragraph("Day", small), Paragraph("Date", small), Paragraph("Plan", small), Paragraph("Overnight", small)]]
    for day in quotation.itinerary:
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
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ])))

    story.append(Paragraph("PACKAGE COST", section))
    cost_rows = [[Paragraph("Particulars", small), Paragraph("Quantity", small), Paragraph("Unit price", small), Paragraph("Total", small)]]
    for item in quotation.items:
        cost_rows.append([
            Paragraph(f"<b>{_text(item.name)}</b><br/>{_text(item.description)}", small),
            Paragraph(_text(item.quantity), small),
            Paragraph(_text(item.unit_price), amount),
            Paragraph(_text(item.total_price), amount),
        ])
    cost_rows.extend([
        [Paragraph("Subtotal", body), "", "", Paragraph(_text(quotation.subtotal), amount)],
        [Paragraph("Discount", body), "", "", Paragraph(_text(quotation.discount_amount), amount)],
        [Paragraph("Tax", body), "", "", Paragraph(_text(quotation.tax_amount), amount)],
        [Paragraph("TOTAL", body), "", "", Paragraph(f"<b>{_text(quotation.total_amount)}</b>", amount)],
    ])
    story.append(Table(cost_rows, colWidths=[92 * mm, 20 * mm, 30 * mm, 32 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6D4")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF1F7")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ])))

    for heading, content in (("INCLUSIONS", quotation.inclusion), ("EXCLUSIONS", quotation.exclusion), ("IMPORTANT NOTES", quotation.important_notes), ("TERMS", quotation.terms_and_conditions)):
        if content:
            story.extend([Paragraph(heading, section), Paragraph(_text(content).replace("\n", "<br/>"), body)])

    document.build(story)
    return buffer.getvalue()


async def generate_and_upload_quotation_pdf(quotation: Quotation) -> dict[str, Any]:
    content = build_quotation_pdf(quotation)
    return await upload_content_to_cloudinary(
        content=content,
        filename=f"{quotation.quotation_code}.pdf",
        content_type="application/pdf",
        sub_folder="temporary-uploads/quotations",
    )