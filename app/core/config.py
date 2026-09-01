from dotenv import load_dotenv
import os

load_dotenv()


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


class Settings:

    IS_DEVELOPMENT: bool = _env_bool("IS_DEVELOPMENT", False)

    DATABASE_URL = _env("DATABASE_URL")

    # Comma-separated frontend origins, for example:
    # https://coochbehartravels.com,https://admin.coochbehartravels.com
    CORS_ORIGINS: tuple[str, ...] = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    )

    # ── JWT & Authentication ─────────────────────────────────────────
    JWT_SECRET_KEY: str = _env("JWT_SECRET_KEY") or "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = _env("JWT_ALGORITHM") or "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    )
    REFRESH_TOKEN_INACTIVITY_HOURS: int = int(
        os.getenv("REFRESH_TOKEN_INACTIVITY_HOURS", "72")
    )

    # ── Cookie Configuration ─────────────────────────────────────────
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    REFRESH_COOKIE_SECURE: bool = _env_bool("REFRESH_COOKIE_SECURE", False)
    REFRESH_COOKIE_SAMESITE: str = (os.getenv("REFRESH_COOKIE_SAMESITE") or ("none" if REFRESH_COOKIE_SECURE else "lax")).lower()
    REFRESH_COOKIE_PATH: str = os.getenv("REFRESH_COOKIE_PATH", "/")
    REFRESH_COOKIE_PARTITIONED: bool = _env_bool("REFRESH_COOKIE_PARTITIONED", False)

    # ── OTP ──────────────────────────────────────────────────────────
    OTP_EXPIRY_SECONDS: int = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    OTP_STATIC_FALLBACK: bool = _env_bool("OTP_STATIC_FALLBACK", False)
    DEV_STATIC_OTP: str = os.getenv("DEV_STATIC_OTP", "123456")

    # ── Google OAuth ─────────────────────────────────────────────────
    GOOGLE_CLIENT_ID_WEB: str | None = _env("GOOGLE_CLIENT_ID_WEB")
    GOOGLE_CLIENT_ID_ANDROID: str | None = _env("GOOGLE_CLIENT_ID_ANDROID")
    GOOGLE_CLIENT_ID_ANDROID_RELEASE: str | None = _env("GOOGLE_CLIENT_ID_ANDROID_RELEASE")
    GOOGLE_CLIENT_ID_ANDROID_DEBUG: str | None = _env("GOOGLE_CLIENT_ID_ANDROID_DEBUG")
    GOOGLE_CLIENT_ID_IOS: str | None = _env("GOOGLE_CLIENT_ID_IOS")
    GOOGLE_CLIENT_SECRET_WEB: str | None = _env("GOOGLE_CLIENT_SECRET_WEB")
    GOOGLE_CLIENT_SECRET_ANDROID: str | None = _env("GOOGLE_CLIENT_SECRET_ANDROID")
    GOOGLE_CLIENT_SECRET_IOS: str | None = _env("GOOGLE_CLIENT_SECRET_IOS")
    GOOGLE_REDIRECT_URI_WEB: str | None = _env("GOOGLE_REDIRECT_URI_WEB")
    GOOGLE_REDIRECT_URI_ANDROID: str | None = _env("GOOGLE_REDIRECT_URI_ANDROID")
    GOOGLE_REDIRECT_URI_IOS: str | None = _env("GOOGLE_REDIRECT_URI_IOS")
    GOOGLE_CLIENT_IDS_ANDROID: tuple[str, ...] = tuple(
        client_id.strip()
        for client_id in (
            GOOGLE_CLIENT_ID_ANDROID,
            GOOGLE_CLIENT_ID_ANDROID_RELEASE,
            GOOGLE_CLIENT_ID_ANDROID_DEBUG,
        )
        if client_id and client_id.strip()
    )
    GOOGLE_CLIENT_IDS_ALLOWED: tuple[str, ...] = tuple(
        {client_id: None for client_id in (
            GOOGLE_CLIENT_ID_WEB,
            *GOOGLE_CLIENT_IDS_ANDROID,
            GOOGLE_CLIENT_ID_IOS,
        ) if client_id and client_id.strip()}
    )
    GMAIL_CREDENTIALS_FILE: str = _env("GMAIL_CREDENTIALS_FILE") or "credentials.json"
    GMAIL_TOKEN_FILE: str = _env("GMAIL_TOKEN_FILE") or "token.json"
    GMAIL_TOKEN_JSON: str | None = _env("GMAIL_TOKEN_JSON")

    # ── SMS ──────────────────────────────────────────────────────────
    SMS_PROVIDER: str | None = _env("SMS_PROVIDER")  # fast2sms, etc.
    SMS_API_KEY: str | None = _env("SMS_API_KEY")


    # ── EMAIL ──────────────────────────────────────────────────────────
    EMAIL_HOST: str | None = _env("EMAIL_HOST")
    EMAIL_PORT: int | None = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME: str | None = _env("EMAIL_USERNAME")
    EMAIL_PASSWORD: str | None = _env("EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = _env_bool("EMAIL_USE_TLS", True)
    EMAIL_USE_SSL: bool = _env_bool("EMAIL_USE_SSL", False)
    EMAIL_DEFAULT_SENDER: str | None = _env("EMAIL_DEFAULT_SENDER")
    EMAIL_FROM_NAME: str = _env("EMAIL_FROM_NAME") or "Coochbehar Travels"

    # ── Cloudinary ───────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str | None = _env("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str | None = _env("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str | None = _env("CLOUDINARY_API_SECRET")

settings = Settings()



