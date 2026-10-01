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
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    REFRESH_TOKEN_INACTIVITY_HOURS: int = int(os.getenv("REFRESH_TOKEN_INACTIVITY_HOURS", "72"))

# ── Cookie Configuration ─────────────────────────────────────────
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    REFRESH_COOKIE_SECURE: bool = _env_bool("REFRESH_COOKIE_SECURE", False)
    REFRESH_COOKIE_SAMESITE: str = (
        os.getenv("REFRESH_COOKIE_SAMESITE") or ("none" if REFRESH_COOKIE_SECURE else "lax")
    ).lower()
    REFRESH_COOKIE_PATH: str = os.getenv("REFRESH_COOKIE_PATH", "/")
    REFRESH_COOKIE_PARTITIONED: bool = _env_bool("REFRESH_COOKIE_PARTITIONED", False)

# ── OTP ──────────────────────────────────────────────────────────
    OTP_EXPIRY_SECONDS: int = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

# ── Google OAuth ─────────────────────────────────────────────────
    GOOGLE_CLIENT_ID_WEB: str | None = _env("GOOGLE_CLIENT_ID_WEB")
    GOOGLE_CLIENT_ID_ANDROID_RELEASE: str | None = _env("GOOGLE_CLIENT_ID_ANDROID_RELEASE")
    GOOGLE_CLIENT_ID_ANDROID_DEBUG: str | None = _env("GOOGLE_CLIENT_ID_ANDROID_DEBUG")

    GOOGLE_CLIENT_IDS_ANDROID: tuple[str, ...] = tuple(
        client_id.strip()
        for client_id in (
            GOOGLE_CLIENT_ID_ANDROID_RELEASE,
            GOOGLE_CLIENT_ID_ANDROID_DEBUG,
        )
        if client_id and client_id.strip()
    )

    GOOGLE_CLIENT_IDS_ALLOWED: tuple[str, ...] = tuple(
        dict.fromkeys(
            client_id.strip()
            for client_id in (
                GOOGLE_CLIENT_ID_WEB,
                *GOOGLE_CLIENT_IDS_ANDROID,
            )
            if client_id and client_id.strip()
        )
    )

# ── SMTP email delivery ──────────────────────────────────────────
    SMTP_HOST: str = _env("SMTP_HOST") or "smtp.hostinger.com"
    SMTP_PORT: int = int(_env("SMTP_PORT") or "465")
    SMTP_USERNAME: str | None = _env("SMTP_USERNAME")
    SMTP_PASSWORD: str | None = _env("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str | None = _env("SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = _env("SMTP_FROM_NAME") or "Coochbehar Travels"

    
    CDN_BASE_URL: str = _env("CDN_BASE_URL") or "https://cdn.gantabyaa.com"
    CDN_STORAGE_PATH: str = _env("CDN_STORAGE_PATH") or "/home/gantabyaa-cdn/htdocs/cdn.gantabyaa.com"
    CDN_MAX_IMAGE_SIZE_MB: int = int(_env("CDN_MAX_IMAGE_SIZE_MB") or "10")
    CDN_MAX_VIDEO_SIZE_MB: int = int(_env("CDN_MAX_VIDEO_SIZE_MB") or "100")
    CDN_MAX_PDF_SIZE_MB: int = int(_env("CDN_MAX_PDF_SIZE_MB") or "20")
    CDN_MAX_VIDEO_DURATION_SECONDS: int = int(
        _env("CDN_MAX_VIDEO_DURATION_SECONDS") or "600"
    )
    CDN_MAX_IMAGE_DIMENSION: int = int(_env("CDN_MAX_IMAGE_DIMENSION") or "4096")
    CDN_IMAGE_COMPRESSION_ENABLED: bool = _env_bool(
        "CDN_IMAGE_COMPRESSION_ENABLED", True
    )
    CDN_VIDEO_COMPRESSION_ENABLED: bool = _env_bool(
        "CDN_VIDEO_COMPRESSION_ENABLED", True
    )
    CDN_ANTIVIRUS_ENABLED: bool = _env_bool("CDN_ANTIVIRUS_ENABLED", True)
    CDN_ANTIVIRUS_HOST: str = _env("CDN_ANTIVIRUS_HOST") or "127.0.0.1"
    CDN_ANTIVIRUS_PORT: int = int(_env("CDN_ANTIVIRUS_PORT") or "3310")
    CDN_UPLOAD_RATE_LIMIT: int = int(_env("CDN_UPLOAD_RATE_LIMIT") or "10")
    CDN_UPLOAD_RATE_WINDOW_SECONDS: int = int(
        _env("CDN_UPLOAD_RATE_WINDOW_SECONDS") or "3600"
    )


settings = Settings()
