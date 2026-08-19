import base64
import json
import logging
from email.message import EmailMessage
from pathlib import Path

from fastapi import HTTPException, status
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
  def _validate_config(self) -> None:
    if settings.GMAIL_TOKEN_JSON:
      return
    token_file = Path(settings.GMAIL_TOKEN_FILE)
    if not token_file.is_file():
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Gmail OAuth token file was not found: {token_file}. Run scripts/generate_token.py first.",
      )

  def _get_gmail_service(self):
    self._validate_config()
    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    if settings.GMAIL_TOKEN_JSON:
      try:
        credentials = Credentials.from_authorized_user_info(
          json.loads(settings.GMAIL_TOKEN_JSON), scopes
        )
      except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail="GMAIL_TOKEN_JSON is not valid Google OAuth token JSON.",
        ) from exc
    else:
      try:
        credentials = Credentials.from_authorized_user_file(settings.GMAIL_TOKEN_FILE, scopes)
      except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail="Gmail token.json is invalid or missing refresh_token. Run scripts/generate_token.py again.",
        ) from exc
    if not credentials.refresh_token:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Gmail OAuth token is missing refresh_token. Run scripts/generate_token.py again.",
      )
    if credentials.expired and credentials.refresh_token:
      credentials.refresh(Request())
      if not settings.GMAIL_TOKEN_JSON:
        Path(settings.GMAIL_TOKEN_FILE).write_text(credentials.to_json(), encoding="utf-8")
    if not credentials.valid:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Gmail OAuth token is invalid. Run scripts/generate_token.py again.",
      )
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)

  def send_otp_email(self, to_email: str, otp: str, expires_in_seconds: int) -> None:
    expires_in_minutes = max(1, expires_in_seconds // 60)
    body = (
      "Your Coochbehar Travels verification code is: "
      f"{otp}\n\n"
      f"This code expires in {expires_in_minutes} minute(s).\n\n"
      "If you did not request this email, you can ignore it."
    )
    try:
      self.send_email(to_email, "Your Coochbehar Travels OTP", body)
    except HTTPException:
      raise
    except Exception as exc:
      logger.exception("Gmail OTP delivery failed")
      detail = "Email OTP failed: Gmail could not deliver the message."
      if settings.IS_DEVELOPMENT:
        detail = f"{detail} Provider error: {exc}"
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
      ) from exc

  def send_email(self, to_email: str, subject: str, body: str) -> dict:
    message = EmailMessage()
    message.set_content(body)
    message["To"] = to_email
    message["Subject"] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return self._get_gmail_service().users().messages().send(
      userId="me",
      body={"raw": encoded_message},
    ).execute()


def send_email(to_email: str, subject: str, body: str) -> dict:
  EmailService().send_email(to_email, subject, body)