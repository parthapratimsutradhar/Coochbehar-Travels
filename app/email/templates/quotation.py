from datetime import date, datetime
from html import escape

from app.email.templates.base import render_detail_table


def _format_date(value: date | datetime | None) -> str:
    return value.strftime("%d %b %Y") if value else "To be confirmed"


def render_quotation_email(
    customer_name: str,
    quotation_code: str,
    tour_name: str,
    travel_date: date | datetime | None,
    return_date: date | datetime | None,
    valid_until: date | datetime | None,
) -> tuple[str, str]:
    display_name = customer_name or "traveler"
    details = (
        ("Quotation reference", quotation_code),
        ("Trip", tour_name),
        ("Departure", _format_date(travel_date)),
        ("Return", _format_date(return_date)),
        ("Offer valid until", _format_date(valid_until)),
    )
    text_body = (
        f"Hello {display_name},\n\n"
        f"Your personalized quotation for {tour_name} is attached as a PDF.\n\n"
        f"Quotation reference: {quotation_code}\n"
        f"Departure: {_format_date(travel_date)}\n"
        f"Return: {_format_date(return_date)}\n"
        f"Offer valid until: {_format_date(valid_until)}\n\n"
        "The attached quotation includes your trip plan and pricing.\n\n"
        "Regards,\nGantabyaa"
    )
    html_content = (
        f'<p style="margin:0 0 8px;color:#52666d;font-size:15px;">Hello {escape(display_name)},</p>'
        '<h1 style="margin:0 0 12px;color:#183b4e;font-size:24px;line-height:1.3;">'
        'Your trip quotation is ready</h1>'
        '<p style="margin:0 0 24px;color:#52666d;font-size:15px;line-height:1.6;">'
        'Your personalized trip plan and pricing are attached as a PDF.</p>'
        f"{render_detail_table(details)}"
    )
    return text_body, html_content