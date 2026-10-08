from email.message import EmailMessage
import smtplib
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.email.service import EmailService
from app.email.social_links import EXPLORE_LINKS, SOCIAL_LINKS
from app.email.templates.base import render_base_email
from app.email.templates.booking import render_booking_email
from app.email.templates.otp import render_otp_email
from app.email.templates.quotation import render_quotation_email


@pytest.mark.parametrize("port, smtp_class", [(465, "SMTP_SSL"), (587, "SMTP")])
def test_send_email_uses_configured_smtp(monkeypatch, port, smtp_class):
    server = MagicMock()
    server.send_message.return_value = {}
    smtp_constructor = MagicMock()
    smtp_constructor.return_value.__enter__.return_value = server
    monkeypatch.setattr("app.email.service.smtplib." + smtp_class, smtp_constructor)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.hostinger.com")
    monkeypatch.setattr(settings, "SMTP_PORT", port)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "mailbox-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_FROM_NAME", "Coochbehar Travels")

    result = EmailService().send_email("customer@example.com", "Subject", "Body")

    assert result == {"accepted": True, "refused_recipients": {}}
    sent_message = server.send_message.call_args.args[0]
    assert isinstance(sent_message, EmailMessage)
    assert sent_message["From"] == "Coochbehar Travels <sender@example.com>"
    assert sent_message["To"] == "customer@example.com"
    assert sent_message["Subject"] == "Subject"
    text_part = next(part for part in sent_message.walk() if part.get_content_type() == "text/plain")
    html_part = next(part for part in sent_message.walk() if part.get_content_type() == "text/html")
    image_part = next(part for part in sent_message.walk() if part.get_content_type() == "image/jpeg")
    assert text_part.get_content() == "Body\n"
    assert 'src="cid:gantabyaa-logo"' in html_part.get_content()
    assert 'align="center"' in html_part.get_content()
    assert 'width="128" height="128"' in html_part.get_content()
    assert image_part["Content-ID"] == "<gantabyaa-logo>"
    assert b"Content-ID: <gantabyaa-logo>" in sent_message.as_bytes()
    if port == 587:
        server.starttls.assert_called_once()
    else:
        smtp_constructor.assert_called_once()


def test_send_email_raises_when_recipient_is_refused(monkeypatch):
    server = MagicMock()
    server.send_message.return_value = {"customer@example.com": (550, b"Mailbox unavailable")}
    smtp_constructor = MagicMock()
    smtp_constructor.return_value.__enter__.return_value = server
    monkeypatch.setattr("app.email.service.smtplib.SMTP_SSL", smtp_constructor)
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "mailbox-password")

    with pytest.raises(smtplib.SMTPRecipientsRefused, match="customer@example.com"):
        EmailService().send_email("customer@example.com", "Subject", "Body")


def test_send_email_supports_private_pdf_attachments(monkeypatch):
    server = MagicMock()
    server.send_message.return_value = {}
    smtp_constructor = MagicMock()
    smtp_constructor.return_value.__enter__.return_value = server
    monkeypatch.setattr("app.email.service.smtplib.SMTP_SSL", smtp_constructor)
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "mailbox-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@example.com")

    EmailService().send_email(
        "customer@example.com",
        "Private document",
        "The PDF is attached.",
        attachments=[("quotation.pdf", b"private pdf bytes", "application/pdf")],
    )

    sent_message = server.send_message.call_args.args[0]
    attachment = next(
        part for part in sent_message.walk()
        if part.get_content_type() == "application/pdf"
    )
    assert attachment.get_filename() == "quotation.pdf"
    assert attachment.get_payload(decode=True) == b"private pdf bytes"


def test_otp_template_is_responsive_and_escapes_dynamic_content(monkeypatch):
    monkeypatch.setattr(
        "app.email.templates.base.SOCIAL_LINKS",
        (
            ("📸 Instagram", "https://instagram.com/gantabyaa"),
            ("👍 Facebook", "javascript:alert(1)"),
            ("▶️ YouTube", "https:youtube.com/@gantabyaa"),
            ("💬 WhatsApp", None),
        ),
    )

    text_body, otp_content = render_otp_email("<img src=x>", 5)
    html_body = render_base_email(otp_content)

    assert "<img src=x>" in text_body
    assert "&lt;img src=x&gt;" in html_body
    assert "Your verification code" in html_body
    assert "Your sign-in code" not in html_body
    assert "complete the action you requested" in html_body
    assert "@media only screen and (max-width:600px)" in html_body
    assert "display:inline-block;margin:0 4px 4px" in html_body
    assert "📸 Instagram" in html_body
    assert "👍 Facebook" in html_body
    assert "▶️ YouTube" in html_body
    assert "💬 WhatsApp" in html_body
    assert 'href="https://instagram.com/gantabyaa"' in html_body
    assert 'href="javascript:alert(1)"' not in html_body
    assert 'href="https:youtube.com/@gantabyaa"' not in html_body


def test_social_links_use_official_hard_coded_destinations():
    rendered = render_base_email("<p>Message</p>")

    assert len(SOCIAL_LINKS) == 4
    for _, url in SOCIAL_LINKS:
        assert f'href="{url}"' in rendered
    assert "Explore more:" in rendered
    for _, url in EXPLORE_LINKS:
        assert f'href="{url}"' in rendered


def test_booking_email_template_includes_booking_details_and_escapes_content():
    text_body, html_body = render_booking_email(
        "<Customer>",
        "BK-12345",
        "Coastal <Escape>",
        None,
        None,
    )
    rendered = render_base_email(html_body)

    assert "BK-12345" in text_body
    assert "To be confirmed" in text_body
    assert "&lt;Customer&gt;" in rendered
    assert "Coastal &lt;Escape&gt;" in rendered


def test_quotation_email_template_includes_offer_validity():
    text_body, html_body = render_quotation_email(
        "Customer",
        "QT-2026-001",
        "Mountain escape",
        None,
        None,
        None,
    )
    rendered = render_base_email(html_body)

    assert "QT-2026-001" in text_body
    assert "Offer valid until: To be confirmed" in text_body
    assert "Your trip quotation is ready" in rendered