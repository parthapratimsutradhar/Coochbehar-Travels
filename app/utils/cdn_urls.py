from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from app.core.config import settings


PUBLIC_CDN_FOLDERS = frozenset(
    {
        "destination-images",
        "hotel-images",
        "profile-picture",
        "review-gallery",
        "room-images",
        "tour-packages",
        "vehicle-images",
    }
)


def _public_asset_path(value: str) -> str | None:
    path = value.strip()
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        cdn = urlsplit(settings.CDN_BASE_URL.rstrip("/"))
        if (parsed.scheme.lower(), parsed.netloc.lower()) != (
            cdn.scheme.lower(),
            cdn.netloc.lower(),
        ) or parsed.query or parsed.fragment:
            return None
        path = parsed.path.lstrip("/")

    parts = path.split("/")
    if (
        len(parts) < 2
        or parts[0] not in PUBLIC_CDN_FOLDERS
        or any(part in {"", ".", ".."} or ":" in part for part in parts)
        or any(character in path for character in ("\\", "%", "?", "#", "\x00"))
    ):
        return None
    return path


def cdn_storage_value(value: str | None) -> str | None:
    """Return a relative CDN path, preserving URLs hosted elsewhere."""
    if value is None:
        return None
    return _public_asset_path(value) or value


def cdn_url_for_value(value: str) -> str:
    path = _public_asset_path(value)
    if path is None:
        return value
    return f"{settings.CDN_BASE_URL.rstrip('/')}/{path}"


def serialize_cdn_urls(value: Any) -> Any:
    if isinstance(value, str):
        return cdn_url_for_value(value)
    if isinstance(value, Mapping):
        return {key: serialize_cdn_urls(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_cdn_urls(item) for item in value]
    return value