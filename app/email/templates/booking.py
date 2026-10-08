from datetime import date
from html import escape

from app.email.templates.base import render_detail_table


def _format_date(value: date | None) -> str:
    return value.strftime("%d %b %Y") if value else "To be confirmed"


def render_booking_email(
    customer_name: str,
    booking_code: str,
    tour_name: str,
    departure_date: date | None,
    return_date: date | None,
) -> tuple[str, str]:
    display_name = customer_name or "traveler"
    details = (
        ("Booking reference", booking_code),
        ("Trip", tour_name),
        ("Departure", _format_date(departure_date)),
        ("Return", _format_date(return_date)),
    )
    text_body = (
        f"Hello {display_name},\n\n"
        "Your booking document is ready. The PDF is attached to this email.\n\n"
        f"Booking reference: {booking_code}\n"
        f"Trip: {tour_name}\n"
        f"Departure: {_format_date(departure_date)}\n"
        f"Return: {_format_date(return_date)}\n\n"
        "Keep the attached document for your travel records.\n\n"
        "Regards,\nGantabyaa"
    )
    html_content = (
        f'<p style="margin:0 0 8px;color:#52666d;font-size:15px;">Hello {escape(display_name)},</p>'
        '<h1 style="margin:0 0 12px;color:#183b4e;font-size:24px;line-height:1.3;">'
        'Your booking details are ready</h1>'
        '<p style="margin:0 0 24px;color:#52666d;font-size:15px;line-height:1.6;">'
        'Your travel document is attached as a PDF. Keep it handy for your records.</p>'
        f"{render_detail_table(details)}"
    )
    return text_body, html_content