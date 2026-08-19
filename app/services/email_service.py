import resend
from fastapi import HTTPException, status

from app.core.config import settings


class EmailService:
  """Resend email delivery for transactional auth messages."""

  def __init__(self) -> None:
    self.api_key = settings.RESEND_API_KEY
    self.sender_email = settings.RESEND_FROM_EMAIL
    self.sender_name = settings.EMAIL_FROM_NAME

  def _validate_config(self) -> None:
    if not self.api_key or not self.sender_email:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Email OTP is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL.",
      )

  def send_otp_email(self, to_email: str, otp: str, expires_in_seconds: int) -> None:
    self._validate_config()

    expires_in_minutes = max(1, expires_in_seconds // 60)
    sender = f"{self.sender_name} <{self.sender_email}>"
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #172026;">
      <p>Your Coochbehar Travels verification code is:</p>
      <p style="font-size: 28px; font-weight: 700; letter-spacing: 4px;">{otp}</p>
      <p>This code expires in {expires_in_minutes} minute(s).</p>
      <p>If you did not request this code, you can ignore this email.</p>
      </body>
    </html>
    """

    try:
      resend.api_key = self.api_key
      resend.Emails.send(
        {
          "from": sender,
          "to": [to_email],
          "subject": "Your Coochbehar Travels OTP",
          "html": html,
        }
      )
    except Exception as exc:
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Email OTP failed: Resend could not deliver the message.",
      ) from exc
