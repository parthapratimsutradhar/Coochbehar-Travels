import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from fastapi import HTTPException, status

from app.core.config import settings


class EmailService:
    """SMTP email delivery for transactional auth messages."""

    def __init__(self) -> None:
        self.host = settings.EMAIL_HOST
        self.port = settings.EMAIL_PORT
        self.username = settings.EMAIL_USERNAME
        self.password = settings.EMAIL_PASSWORD
        self.sender_email = settings.EMAIL_DEFAULT_SENDER or settings.EMAIL_USERNAME
        self.sender_name = settings.EMAIL_FROM_NAME

    def _validate_config(self) -> None:
        if not all([self.host, self.port, self.username, self.password, self.sender_email]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email OTP is not configured. Set EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, and EMAIL_DEFAULT_SENDER.",
            )

        if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email config is invalid. Use either EMAIL_USE_TLS or EMAIL_USE_SSL, not both.",
            )

    def send_otp_email(self, to_email: str, otp: str, expires_in_seconds: int) -> None:
        self._validate_config()

        expires_in_minutes = max(1, expires_in_seconds // 60)
        subject = "Your Coochbehar Travels OTP"

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.sender_name, self.sender_email))
        message["To"] = to_email
        message.set_content(
            "\n".join(
                [
                    "Your Coochbehar Travels verification code is:",
                    "",
                    otp,
                    "",
                    f"This code expires in {expires_in_minutes} minute(s).",
                    "If you did not request this code, you can ignore this email.",
                ]
            )
        )
        message.add_alternative(
            f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #172026;">
                <p>Your Coochbehar Travels verification code is:</p>
                <p style="font-size: 28px; font-weight: 700; letter-spacing: 4px;">{otp}</p>
                <p>This code expires in {expires_in_minutes} minute(s).</p>
                <p>If you did not request this code, you can ignore this email.</p>
              </body>
            </html>
            """,
            subtype="html",
        )

        try:
            if settings.EMAIL_USE_SSL:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as smtp:
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                    if settings.EMAIL_USE_TLS:
                        smtp.starttls()
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Email OTP failed: SMTP authentication failed. Check EMAIL_USERNAME and EMAIL_PASSWORD/app password.",
            ) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Email OTP failed: could not connect to SMTP server {self.host}:{self.port}.",
            ) from exc
        except smtplib.SMTPException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Email OTP failed: {exc}",
            ) from exc
