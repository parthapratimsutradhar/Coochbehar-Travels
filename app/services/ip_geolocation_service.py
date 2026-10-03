"""Best-effort visitor geolocation using a local GeoLite2 City database."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import threading
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 24 * 60 * 60
_MAX_CACHE_ENTRIES = 2048
_location_cache: dict[str, tuple[float, dict[str, str]]] = {}
_reader_lock = threading.Lock()
_reader = None
_reader_path: Path | None = None
_warned_missing_database = False


def _get_reader():
    global _reader, _reader_path, _warned_missing_database

    path = Path(settings.GEOLITE2_CITY_DB_PATH).expanduser().resolve()
    if not path.is_file():
        if not _warned_missing_database:
            logger.warning("GeoLite2 City database is not available at %s", path)
            _warned_missing_database = True
        return None

    with _reader_lock:
        if _reader is not None and _reader_path == path:
            return _reader
        try:
            from geoip2.database import Reader

            if _reader is not None:
                _reader.close()
            _reader = Reader(str(path))
            _reader_path = path
            _warned_missing_database = False
        except Exception:
            logger.exception("Could not open GeoLite2 City database at %s", path)
            _reader = None
            _reader_path = None
        return _reader


def _lookup_city(ip_address: str) -> dict[str, str]:
    reader = _get_reader()
    if reader is None:
        return {}

    try:
        result = reader.city(ip_address)
    except Exception as exc:
        try:
            from geoip2.errors import AddressNotFoundError
        except ImportError:
            AddressNotFoundError = ()
        if AddressNotFoundError and isinstance(exc, AddressNotFoundError):
            return {}
        logger.debug("GeoLite2 lookup failed for visitor IP", exc_info=True)
        return {}

    country = getattr(getattr(result, "country", None), "name", None)
    subdivisions = getattr(result, "subdivisions", None)
    state = getattr(getattr(subdivisions, "most_specific", None), "name", None)
    city = getattr(getattr(result, "city", None), "name", None)
    values = {"country": country, "state": state, "city": city}
    return {
        key: value.strip()
        for key, value in values.items()
        if isinstance(value, str) and value.strip()
    }


async def lookup_ip_location(ip_address: str | None) -> dict[str, str]:
    if not ip_address:
        return {}

    try:
        ip = ipaddress.ip_address(ip_address.strip())
    except ValueError:
        return {}
    if not ip.is_global:
        return {}

    key = ip.compressed
    now = time.monotonic()
    cached = _location_cache.get(key)
    if cached and cached[0] > now:
        return cached[1].copy()

    location = await asyncio.to_thread(_lookup_city, key)
    if len(_location_cache) >= _MAX_CACHE_ENTRIES:
        _location_cache.pop(next(iter(_location_cache)))
    _location_cache[key] = (now + _CACHE_TTL_SECONDS, location)
    return location.copy()