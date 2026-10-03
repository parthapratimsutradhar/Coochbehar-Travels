from email.message import EmailMessage
import smtplib
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services.email_service import EmailService


@pytest.mark.parametrize("port, smtp_class", [(465, "SMTP_SSL"), (587, "SMTP")])
def test_send_email_uses_configured_smtp(monkeypatch, port, smtp_class):
    server = MagicMock()
    server.send_message.return_value = {}
    smtp_constructor = MagicMock()
    smtp_constructor.return_value.__enter__.return_value = server
    monkeypatch.setattr("app.services.email_service.smtplib." + smtp_class, smtp_constructor)
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
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP_SSL", smtp_constructor)
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
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP_SSL", smtp_constructor)
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