from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # ── OTP ──────────────────────────────────────────────────────────
    OTP_EXPIRY_SECONDS: int = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

    # ── Google OAuth ─────────────────────────────────────────────────
    GOOGLE_CLIENT_ID_WEB: str | None = os.getenv("GOOGLE_CLIENT_ID_WEB")
    GOOGLE_CLIENT_ID_ANDROID: str | None = os.getenv("GOOGLE_CLIENT_ID_ANDROID")
    GOOGLE_CLIENT_ID_IOS: str | None = os.getenv("GOOGLE_CLIENT_ID_IOS")
    GOOGLE_CLIENT_SECRET_WEB: str | None = os.getenv("GOOGLE_CLIENT_SECRET_WEB")
    GOOGLE_CLIENT_SECRET_ANDROID: str | None = os.getenv("GOOGLE_CLIENT_SECRET_ANDROID")
    GOOGLE_CLIENT_SECRET_IOS: str | None = os.getenv("GOOGLE_CLIENT_SECRET_IOS")
    GOOGLE_REDIRECT_URI_WEB: str | None = os.getenv("GOOGLE_REDIRECT_URI_WEB")
    GOOGLE_REDIRECT_URI_ANDROID: str | None = os.getenv("GOOGLE_REDIRECT_URI_ANDROID")
    GOOGLE_REDIRECT_URI_IOS: str | None = os.getenv("GOOGLE_REDIRECT_URI_IOS")

    # ── SMS ──────────────────────────────────────────────────────────
    SMS_PROVIDER: str | None = os.getenv("SMS_PROVIDER")  # fast2sms, etc.
    SMS_API_KEY: str | None = os.getenv("SMS_API_KEY")


    # ── EMAIL ──────────────────────────────────────────────────────────
    EMAIL_HOST: str | None = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int | None = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME: str | None = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    EMAIL_USE_SSL: bool = os.getenv("EMAIL_USE_SSL", "False").lower() in ("true", "1", "yes")
    EMAIL_DEFAULT_SENDER: str | None = os.getenv("EMAIL_DEFAULT_SENDER")



settings = Settings()