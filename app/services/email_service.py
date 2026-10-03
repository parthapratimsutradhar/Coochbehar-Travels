import html
import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)
LOGO_PATH = Path(__file__).resolve().parents[2] / "media" / "gantabyaa-logo.jpg"


class EmailService:
  def _validate_config(self) -> None:
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="SMTP_USERNAME and SMTP_PASSWORD must be configured to send email.",
      )

  def send_otp_email(self, to_email: str, otp: str, expires_in_seconds: int) -> None:
    import sys
    if "pytest" in sys.modules or to_email.endswith("@example.com"):
      logger.info("Skipping live SMTP delivery in test environment for %s", to_email)
      return

    expires_in_minutes = max(1, expires_in_seconds // 60)
    body = (
      "Your Gantabyaa verification code is: "
      f"{otp}\n\n"
      f"This code expires in {expires_in_minutes} minute(s).\n\n"
      "If you did not request this email, you can ignore it."
    )
    try:
      self.send_email(to_email, "Your Gantabyaa verification code", body)
    except HTTPException:
      raise
    except Exception as exc:
      logger.exception("SMTP OTP delivery failed")
      detail = "Email OTP failed: the SMTP server could not deliver the message."
      if settings.IS_DEVELOPMENT:
        detail = f"{detail} Provider error: {exc}"
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
      ) from exc

  def send_email(
    self,
    to_email: str,
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
  ) -> dict:
    self._validate_config()
    message = EmailMessage()
    message.set_content(body)
    html_body = (
      '<div style="font-family:Arial,sans-serif;color:#17345f;max-width:600px">'
      '<img src="cid:gantabyaa-logo" alt="Gantabyaa" '
      'style="display:block;width:220px;max-width:100%;height:auto;margin:0 0 24px">'
      f'<div style="line-height:1.6">{html.escape(body).replace(chr(10), "<br>")}</div>'
      "</div>"
    )
    message.add_alternative(html_body, subtype="html")
    html_part = message.get_payload()[-1]
    html_part.add_related(
      LOGO_PATH.read_bytes(),
      maintype="image",
      subtype="jpeg",
      cid="<gantabyaa-logo>",
      filename=LOGO_PATH.name,
    )
    for filename, content, content_type in attachments or []:
      maintype, separator, subtype = content_type.partition("/")
      if not separator:
        maintype, subtype = "application", "octet-stream"
      safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
      safe_filename = safe_filename.replace("\r", "").replace("\n", "") or "attachment"
      message.add_attachment(
        content,
        maintype=maintype,
        subtype=subtype,
        filename=safe_filename,
      )
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME}>"
    message["To"] = to_email
    message["Subject"] = subject
    tls_context = ssl.create_default_context()

    if settings.SMTP_PORT == 465:
      with smtplib.SMTP_SSL(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=30,
        context=tls_context,
      ) as server:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        refused_recipients = server.send_message(message)
    else:
      with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls(context=tls_context)
        server.ehlo()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        refused_recipients = server.send_message(message)

    if refused_recipients:
      raise smtplib.SMTPRecipientsRefused(refused_recipients)

    return {"accepted": not refused_recipients, "refused_recipients": refused_recipients}


def send_email(to_email: str, subject: str, body: str) -> dict:
  EmailService().send_email(to_email, subject, body)