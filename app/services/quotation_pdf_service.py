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
from app.services.cdn_service import upload_content_to_cdn


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
        Paragraph("Tour & Sightseeing Package", styles["Heading3"]),
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
        if item.hotel or item.vehicle:
            continue
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
    return await upload_content_to_cdn(
        content=content,
        filename=f"{quotation.quotation_code}.pdf",
        content_type="application/pdf",
        target_folder="temporary-uploads",
    )