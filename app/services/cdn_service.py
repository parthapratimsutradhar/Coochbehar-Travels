import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import socket
import stat
import struct
import subprocess
import tempfile
import time
import warnings
from io import BytesIO
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import delete
from starlette.datastructures import Headers

from app.core.config import settings
from app.models.cdn_upload_rate_limit import CDNUploadRateLimit


logger = logging.getLogger(__name__)
CDN_ROOT = Path(settings.CDN_STORAGE_PATH).resolve()
CDN_BASE_URL = settings.CDN_BASE_URL.rstrip("/")

TEMP_FOLDER = "temporary-uploads"
TEMP_UPLOAD_RETENTION_SECONDS = 24 * 60 * 60

PUBLIC_FOLDERS = {
    "profile-picture",
    "tour-packages",
    "review-gallery",
    "destination-images",
    "hotel-images",
    "vehicle-images",
    "room-images",
}

PRIVATE_DOCUMENT_FOLDERS = {
    "private/customer-documents",
    "private/admin-documents",
}
ALLOWED_FOLDERS = PUBLIC_FOLDERS | PRIVATE_DOCUMENT_FOLDERS | {TEMP_FOLDER}

CDN_ROOT.mkdir(parents=True, exist_ok=True)

for folder in PUBLIC_FOLDERS | {TEMP_FOLDER} | PRIVATE_DOCUMENT_FOLDERS:
    (CDN_ROOT / folder).mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/mov": ".mov",
    "video/webm": ".webm",
    "application/pdf": ".pdf",
}

MAX_IMAGE_SIZE = settings.CDN_MAX_IMAGE_SIZE_MB * 1024 * 1024
MAX_VIDEO_SIZE = settings.CDN_MAX_VIDEO_SIZE_MB * 1024 * 1024
MAX_PDF_SIZE = settings.CDN_MAX_PDF_SIZE_MB * 1024 * 1024
_UPLOAD_CONCURRENCY = asyncio.Semaphore(1)
_MIME_TO_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/avif": "AVIF",
    "image/gif": "GIF",
}
_FORMAT_TO_MIME = {value: key for key, value in _MIME_TO_FORMAT.items()}
_CLIENT_EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/mov",
    ".webm": "video/webm",
    ".pdf": "application/pdf",
}
_VIDEO_EXTENSIONS = {"video/mp4": ".mp4", "video/mov": ".mov", "video/webm": ".webm"}
_TEMP_FILENAME_RE = re.compile(
    r"^[0-9a-f]{32}\.(?:jpg|png|webp|avif|gif|mp4|mov|webm|pdf)$"
)
_ANTIVIRUS_STATUS = "disabled" if not settings.CDN_ANTIVIRUS_ENABLED else "unchecked"


def _validate_folder(folder: str, *, allow_temp: bool = True) -> str:
    folder = folder.strip()

    if folder not in ALLOWED_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported CDN folder",
        )

    if not allow_temp and folder == TEMP_FOLDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Temporary folder is not allowed here",
        )

    return folder


def _validate_content_type(content_type: str) -> str:
    content_type = content_type.split(";", 1)[0].strip().lower()
    extension = ALLOWED_CONTENT_TYPES.get(content_type)

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    return extension


def _max_file_size(content_type: str) -> int:
    if content_type.startswith("image/"):
        return settings.CDN_MAX_IMAGE_SIZE_MB * 1024 * 1024
    elif content_type.startswith("video/"):
        return settings.CDN_MAX_VIDEO_SIZE_MB * 1024 * 1024
    elif content_type == "application/pdf":
        return settings.CDN_MAX_PDF_SIZE_MB * 1024 * 1024
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )


def _resolve_path(relative_path: str) -> Path:
    relative_path = _validate_relative_path(relative_path)
    path = (CDN_ROOT / relative_path).resolve()

    if path != CDN_ROOT and CDN_ROOT not in path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CDN file path",
        )

    current = CDN_ROOT
    for component in Path(relative_path).parts:
        current = current / component
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid CDN file path",
                )

    return path


def _validate_relative_path(relative_path: str) -> str:
    if not isinstance(relative_path, str) or not relative_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CDN file path",
        )
    path = relative_path.strip()
    parts = path.split("/")

    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or "%" in path
        or "?" in path
        or "#" in path
        or PureWindowsPath(path).is_absolute()
        or any(part in {"", ".", ".."} or ":" in part for part in parts)
        or "\x00" in path
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CDN file path",
        )

    return "/".join(parts)


def _private_work_directory() -> Path:
    staging_root = CDN_ROOT / ".upload-staging"
    if staging_root.is_symlink():
        raise RuntimeError("Private staging directory is unsafe")
    staging_root.mkdir(mode=0o700, exist_ok=True)
    if not staging_root.resolve().is_relative_to(CDN_ROOT):
        raise RuntimeError("Private staging directory is outside the CDN root")
    os.chmod(staging_root, 0o700)
    return Path(tempfile.mkdtemp(prefix="upload-", dir=staging_root))


def _temporary_upload_relative_path(reference: str) -> str:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        cdn_origin = urlsplit(CDN_BASE_URL)
        if (parsed.scheme.lower(), parsed.netloc.lower()) != (
            cdn_origin.scheme.lower(),
            cdn_origin.netloc.lower(),
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File reference must point to a temporary CDN upload",
            )
        if parsed.query or parsed.fragment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporary upload references cannot include a query or fragment",
            )
        relative_path = parsed.path.lstrip("/")
    elif parsed.path.startswith("/api/v1/public/files/temporary/"):
        if parsed.query or parsed.fragment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporary upload references cannot include a query or fragment",
            )
        filename = parsed.path.removeprefix("/api/v1/public/files/temporary/")
        relative_path = f"{TEMP_FOLDER}/{filename}"
    else:
        relative_path = reference

    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if (
        len(parts) != 2
        or parts[0] != TEMP_FOLDER
        or not _TEMP_FILENAME_RE.fullmatch(parts[1])
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only server-generated temporary uploads can be used",
        )
    return relative_path


async def _stage_upload(file: UploadFile, path: Path, content_type: str) -> int:
    total = 0
    maximum = _max_file_size(content_type)
    try:
        with path.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > maximum:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds the configured size limit",
                    )
                await _run_in_worker(output.write, chunk)
            await _run_in_worker(output.flush)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    return total


def _validate_image(path: Path, claimed_type: str) -> tuple[str, bool]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                actual_format = (image.format or "").upper()
                actual_type = _FORMAT_TO_MIME.get(actual_format)
                if actual_type != claimed_type:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="File content does not match the declared type",
                    )
                if image.width * image.height > 20_000_000:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Image dimensions exceed the safe processing limit",
                    )
                animated = bool(getattr(image, "is_animated", False))
                for frame_index in range(getattr(image, "n_frames", 1)):
                    image.seek(frame_index)
                    image.load()
        return actual_format, animated
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image dimensions exceed the safe processing limit",
        ) from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image file is malformed or corrupted",
        ) from None


def _validate_pdf(path: Path) -> None:
    from pypdf import PdfReader

    try:
        with path.open("rb") as source:
            reader = PdfReader(source, strict=True)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not accepted")
            len(reader.pages)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF file is malformed or corrupted",
        ) from None


def _connect_to_clamd(timeout: float) -> socket.socket:
    if settings.CDN_ANTIVIRUS_SOCKET:
        if not hasattr(socket, "AF_UNIX"):
            raise OSError("Unix-domain sockets are unavailable on this platform")
        scanner = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            scanner.settimeout(timeout)
            scanner.connect(settings.CDN_ANTIVIRUS_SOCKET)
            return scanner
        except OSError:
            scanner.close()
            raise

    endpoint = (settings.CDN_ANTIVIRUS_HOST, settings.CDN_ANTIVIRUS_PORT)
    return socket.create_connection(endpoint, timeout=timeout)


def _clamd_command(command: bytes) -> str:
    with _connect_to_clamd(timeout=5) as scanner:
        scanner.settimeout(30)
        scanner.sendall(command)
        response = bytearray()
        while len(response) < 4096:
            block = scanner.recv(1024)
            if not block:
                break
            response.extend(block)
            if b"\0" in block or b"\n" in block:
                break
    return response.decode("utf-8", errors="replace").strip("\0\r\n")


def check_antivirus_available() -> bool:
    global _ANTIVIRUS_STATUS
    if not settings.CDN_ANTIVIRUS_ENABLED:
        _ANTIVIRUS_STATUS = "disabled"
        return False
    try:
        available = _clamd_command(b"zPING\0") == "PONG"
    except OSError:
        available = False
    _ANTIVIRUS_STATUS = "available" if available else "unavailable"
    return available


def antivirus_health_status() -> str:
    return _ANTIVIRUS_STATUS


def _scan_with_clamd(path: Path) -> None:
    try:
        with _connect_to_clamd(timeout=5) as scanner:
            scanner.settimeout(60)
            scanner.sendall(b"zINSTREAM\0")
            with path.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    scanner.sendall(struct.pack("!I", len(chunk)))
                    scanner.sendall(chunk)
            scanner.sendall(struct.pack("!I", 0))
            response = bytearray()
            while len(response) < 4096:
                block = scanner.recv(1024)
                if not block:
                    break
                response.extend(block)
                if b"\0" in block or b"\n" in block:
                    break
        result = response.decode("utf-8", errors="replace").strip("\0\r\n")
    except OSError as exc:
        logger.exception("ClamAV scan could not complete")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Antivirus scanning is temporarily unavailable",
        ) from exc

    if result.endswith("FOUND"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file was rejected by antivirus scanning",
        )
    if not result.endswith("OK"):
        logger.error("ClamAV returned an unsuccessful scan result")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Antivirus scanning is temporarily unavailable",
        )


def _compress_image(source: Path, output: Path, image_format: str) -> Path:
    if image_format == "GIF":
        return source

    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            width, height = image.size
            max_dimension = max(1, settings.CDN_MAX_IMAGE_DIMENSION)
            if max(width, height) > max_dimension:
                scale = max_dimension / max(width, height)
                new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            options: dict[str, Any] = {}
            if image_format == "JPEG":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                options = {"quality": 88, "optimize": True, "progressive": True}
            elif image_format == "PNG":
                options = {"optimize": True, "compress_level": 6}
            elif image_format == "WEBP":
                options = {"quality": 88, "method": 4}
            elif image_format == "AVIF":
                options = {"quality": 82}
            image.save(output, format=image_format, **options)
        if output.stat().st_size < source.stat().st_size:
            return output
    except (OSError, ValueError, KeyError):
        output.unlink(missing_ok=True)
        if image_format == "AVIF":
            logger.info("Pillow AVIF encoder unavailable; retaining validated source")
            return source
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image could not be safely processed",
        ) from None
    output.unlink(missing_ok=True)
    return source


def _probe_video(path: Path, claimed_type: str) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video validation is temporarily unavailable",
        )
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-max_alloc", "50000000",
                "-probesize", "10000000",
                "-analyzeduration", "10000000",
                "-protocol_whitelist", "file,pipe",
                "-show_entries", "format=format_name,duration:format_tags=major_brand",
                "-show_entries", "stream=codec_type,codec_name,width,height",
                "-of", "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        details = json.loads(result.stdout)
        video_streams = [
            stream for stream in details.get("streams", [])
            if stream.get("codec_type") == "video"
        ]
        if not video_streams:
            raise ValueError("Missing video stream")
        duration = float(details.get("format", {}).get("duration", "nan"))
        width = int(video_streams[0].get("width", 0))
        height = int(video_streams[0].get("height", 0))
        format_names = details.get("format", {}).get("format_name", "").split(",")
        major_brand = details.get("format", {}).get("tags", {}).get("major_brand", "")
        with path.open("rb") as source:
            header = source.read(64)
        if not video_streams or not duration or duration != duration or not width or not height:
            raise ValueError("Missing video stream or duration")
        if width * height > 20_000_000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Video dimensions exceed the safe processing limit",
            )
        if duration > settings.CDN_MAX_VIDEO_DURATION_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Video exceeds the configured duration limit",
            )
        if claimed_type == "video/webm":
            matches = header.startswith(b"\x1a\x45\xdf\xa3") and "webm" in format_names
        else:
            is_quicktime = major_brand.lower().startswith("qt")
            is_iso_media = "mov" in format_names and not is_quicktime
            matches = b"ftyp" in header[:32] and (
                (claimed_type == "video/mov" and is_quicktime)
                or (claimed_type == "video/mp4" and is_iso_media)
            )
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File content does not match the declared type",
            )
        return {
            "duration": duration,
            "video_codec": video_streams[0].get("codec_name"),
            "audio_codecs": [
                stream.get("codec_name")
                for stream in details.get("streams", [])
                if stream.get("codec_type") == "audio"
            ],
        }
    except HTTPException:
        raise
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, AttributeError):
        logger.exception("Uploaded video failed ffprobe validation")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Video file is malformed or corrupted",
        ) from None


def _process_video(
    source: Path,
    work_dir: Path,
    claimed_type: str,
    details: dict[str, Any],
) -> tuple[Path, str, str]:
    extension = _VIDEO_EXTENSIONS[claimed_type]
    if not settings.CDN_VIDEO_COMPRESSION_ENABLED:
        return source, claimed_type, extension

    file_size = source.stat().st_size
    needs_compression = (
        file_size > 25 * 1024 * 1024
        or details["video_codec"] != "h264"
        or any(codec != "aac" for codec in details["audio_codecs"])
    )
    if not needs_compression:
        return source, claimed_type, extension

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video compression is temporarily unavailable",
        )

    compressed = work_dir / f"{uuid4().hex}.mp4"
    try:
        subprocess.run(
            [
                ffmpeg,
                "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-max_alloc", "50000000", "-filter_threads", "1",
                "-protocol_whitelist", "file,pipe",
                "-i", str(source),
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
                "-maxrate", "6M", "-bufsize", "12M", "-threads", "1",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-fs",
                str(settings.CDN_MAX_VIDEO_SIZE_MB * 1024 * 1024),
                "-f", "mp4", str(compressed),
            ],
            check=True,
            capture_output=True,
            timeout=max(120, settings.CDN_MAX_VIDEO_DURATION_SECONDS * 2),
        )
        _probe_video(compressed, "video/mp4")
        compressed_size = compressed.stat().st_size
        if compressed_size < file_size:
            return compressed, "video/mp4", ".mp4"
    except HTTPException:
        raise
    except (subprocess.SubprocessError, OSError):
        logger.exception("FFmpeg video processing failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Video processing failed",
        ) from None
    compressed.unlink(missing_ok=True)
    return source, claimed_type, extension


async def _run_in_worker(function: Any, *args: Any) -> Any:
    worker = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        try:
            await worker
        except Exception:
            logger.exception("Upload worker failed during request cancellation")
        raise


async def _upload_file_to_folder(
    file: UploadFile,
    target_folder: str,
) -> dict[str, Any]:
    target_folder = _validate_folder(target_folder)
    if target_folder in PRIVATE_DOCUMENT_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Private documents must be promoted from temporary storage",
        )
    async with _UPLOAD_CONCURRENCY:
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        extension = _validate_content_type(content_type)
        client_extension = Path(file.filename or "").suffix.lower()
        declared_extension_type = _CLIENT_EXTENSION_TYPES.get(client_extension)
        if declared_extension_type and declared_extension_type != content_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Filename extension does not match the declared type",
            )
        work_dir: Path | None = None
        destination: Path | None = None
        published = False
        try:
            work_dir = _private_work_directory()
            original = work_dir / "source"
            size = await _stage_upload(file, original, content_type)

            image_format = None
            image_animated = False
            video_details = None
            if content_type.startswith("image/"):
                image_format, image_animated = await _run_in_worker(
                    _validate_image, original, content_type
                )
            elif content_type.startswith("video/"):
                video_details = await _run_in_worker(
                    _probe_video, original, content_type
                )
            else:
                with original.open("rb") as source:
                    pdf_signature = source.read(5) == b"%PDF-"
                if not pdf_signature:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="File content does not match the declared type",
                    )
                await _run_in_worker(_validate_pdf, original)

            if settings.CDN_ANTIVIRUS_ENABLED:
                await _run_in_worker(_scan_with_clamd, original)

            selected = original
            if (
                content_type.startswith("image/")
                and settings.CDN_IMAGE_COMPRESSION_ENABLED
                and not image_animated
            ):
                selected = await _run_in_worker(
                    _compress_image,
                    original,
                    work_dir / f"compressed{extension}",
                    image_format,
                )
            elif content_type.startswith("video/"):
                selected, content_type, extension = await _run_in_worker(
                    _process_video,
                    original,
                    work_dir,
                    content_type,
                    video_details,
                )

            filename = f"{uuid4().hex}{extension}"
            relative_path = f"{target_folder}/{filename}"
            destination = _resolve_path(relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination = _resolve_path(relative_path)
            if destination.exists():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Unable to allocate a unique upload name",
                )
            os.chmod(selected, 0o640)
            os.link(selected, destination, follow_symlinks=False)
            published = True
            return {
                "path": relative_path,
                "url": (
                    build_temporary_download_url(relative_path)
                    if target_folder == TEMP_FOLDER
                    else build_cdn_url(relative_path)
                ),
                "filename": filename,
                "content_type": content_type,
                "bytes": size if selected == original else selected.stat().st_size,
            }
        except HTTPException:
            if published and destination:
                destination.unlink(missing_ok=True)
            raise
        except Exception as exc:
            if published and destination:
                destination.unlink(missing_ok=True)
            logger.exception("CDN upload processing failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File upload processing failed",
            ) from exc
        finally:
            if work_dir:
                try:
                    shutil.rmtree(work_dir)
                except OSError as exc:
                    logger.exception("Could not clean private CDN upload staging")
                    if published and destination:
                        destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="File upload cleanup failed",
                    ) from exc


async def upload_file_to_cdn(file: UploadFile) -> dict[str, Any]:
    return await _upload_file_to_folder(file, TEMP_FOLDER)


async def upload_content_to_cdn(
    content: bytes,
    filename: str,
    content_type: str,
    target_folder: str,
) -> dict[str, Any]:
    folder = _validate_folder(target_folder)
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )
    return await _upload_file_to_folder(file, folder)


async def promote_cdn_asset(
    url_or_path: str | None,
    target_folder: str,
) -> dict[str, str]:
    target_folder = _validate_folder(target_folder, allow_temp=False)
    if not url_or_path:
        return {"url": "", "path": ""}

    cleaned = url_or_path.strip()
    parsed = urlsplit(cleaned)
    is_private_destination = target_folder in PRIVATE_DOCUMENT_FOLDERS

    if is_private_destination:
        relative_path = _temporary_upload_relative_path(cleaned)
        promoted = promote_temp_file(relative_path, target_folder)
        return {"url": "", "path": promoted["path"]}

    if parsed.scheme or parsed.netloc:
        cdn_origin = urlsplit(CDN_BASE_URL)
        if parsed.netloc.lower() == cdn_origin.netloc.lower():
            if parsed.scheme.lower() != cdn_origin.scheme.lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="CDN asset URL has an invalid scheme",
                )
            relative_path = _validate_relative_path(parsed.path.lstrip("/"))
            if relative_path.startswith(f"{TEMP_FOLDER}/"):
                relative_path = _temporary_upload_relative_path(cleaned)
                promoted = promote_temp_file(relative_path, target_folder)
                return {"url": promoted["url"], "path": promoted["path"]}
            if relative_path.split("/", 1)[0] in PUBLIC_FOLDERS:
                return {"url": cleaned, "path": relative_path}
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="CDN path is not a public asset",
            )

        if (
            parsed.scheme.lower() in {"http", "https"}
            and parsed.hostname
            and not parsed.username
            and not parsed.password
        ):
            return {"url": cleaned, "path": ""}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Asset URL is invalid",
        )

    if cleaned.startswith("/"):
        relative_path = _temporary_upload_relative_path(cleaned)
    else:
        relative_path = _validate_relative_path(cleaned)
    if relative_path.startswith(f"{TEMP_FOLDER}/"):
        promoted = promote_temp_file(relative_path, target_folder)
        return {"url": promoted["url"], "path": promoted["path"]}
    if relative_path.split("/", 1)[0] in PUBLIC_FOLDERS:
        return {"url": build_cdn_url(relative_path), "path": relative_path}
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Asset path is not a temporary upload or public asset",
    )


def _validate_google_picture_url(picture_url: str) -> None:
    try:
        parsed = httpx.URL(picture_url)
    except httpx.InvalidURL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture URL is invalid",
        ) from None

    host = parsed.host.lower().rstrip(".") if parsed.host else ""
    trusted_host = host == "googleusercontent.com" or host.endswith(
        ".googleusercontent.com"
    )
    if (
        parsed.scheme != "https"
        or not trusted_host
        or bool(parsed.username)
        or bool(parsed.password)
        or (parsed.port is not None and parsed.port != 443)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture URL is invalid",
        )


async def upload_google_profile_picture(picture_url: str) -> str:
    _validate_google_picture_url(picture_url)
    max_size = settings.CDN_MAX_IMAGE_SIZE_MB * 1024 * 1024
    work_dir = _private_work_directory()
    source = work_dir / "google-profile-picture"
    published_path: str | None = None

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            async with client.stream("GET", picture_url) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Unable to download Google profile picture",
                    )
                content_type = response.headers.get("content-type", "")
                content_type = content_type.split(";", 1)[0].strip().lower()
                if not content_type.startswith("image/"):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Google profile picture has an unsupported type",
                    )
                try:
                    extension = _validate_content_type(content_type)
                except HTTPException:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Google profile picture has an unsupported type",
                    ) from None

                with source.open("xb") as content:
                    total = 0
                    async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                        total += len(chunk)
                        if total > max_size:
                            raise HTTPException(
                                status_code=status.HTTP_502_BAD_GATEWAY,
                                detail="Google profile picture exceeds the configured size limit",
                            )
                        await _run_in_worker(content.write, chunk)
                    if total == 0:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Google profile picture is empty",
                        )
                    await _run_in_worker(content.flush)

        with source.open("rb") as content:
            file = UploadFile(
                filename=f"google-profile-picture{extension}",
                file=content,
                headers=Headers({"content-type": content_type}),
            )
            result = await _upload_file_to_folder(file, "profile-picture")
            published_path = result["path"]
            return result["url"]
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        logger.warning(
            "Google profile picture download failed: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to download Google profile picture",
        ) from None
    finally:
        try:
            shutil.rmtree(work_dir)
        except OSError as exc:
            logger.exception("Could not clean private Google profile-picture staging")
            if published_path:
                try:
                    delete_cdn_file(published_path)
                except OSError:
                    logger.exception("Could not remove profile picture after staging cleanup failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile picture cleanup failed",
            ) from exc


def enforce_upload_rate_limit(db: Any, actor: Any, client_ip: str | None) -> None:
    actor_value, actor_type = actor if isinstance(actor, tuple) else (actor, "ACTOR")
    if actor_type == "ADMIN":
        limit = settings.CDN_ADMIN_UPLOAD_RATE_LIMIT
        window_seconds = settings.CDN_ADMIN_UPLOAD_RATE_WINDOW_SECONDS
    else:
        limit = settings.CDN_UPLOAD_RATE_LIMIT
        window_seconds = settings.CDN_UPLOAD_RATE_WINDOW_SECONDS
    if limit < 1 or window_seconds < 1:
        logger.error("CDN upload rate-limit settings must be positive")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload rate limiting is temporarily unavailable",
        )

    actor_id = getattr(actor_value, "id", None)
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload rate limiting is temporarily unavailable",
        )

    current_time = int(time.time())
    window_start = current_time - (current_time % window_seconds)
    identifiers = [f"actor:{actor_type}:{actor_id}"]
    if client_ip:
        identifiers.append(f"ip:{client_ip}")
    bucket_keys = [hashlib.sha256(value.encode("utf-8")).hexdigest() for value in identifiers]
    table = CDNUploadRateLimit.__table__
    insert_for_dialect = {
        "postgresql": postgres_insert,
        "sqlite": sqlite_insert,
    }.get(db.bind.dialect.name)
    if insert_for_dialect is None:
        logger.error("Unsupported database dialect for upload rate limiting")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload rate limiting is temporarily unavailable",
        )

    try:
        counts = []
        for bucket_key in bucket_keys:
            statement = insert_for_dialect(table).values(
                bucket_key=bucket_key,
                window_start=window_start,
                count=1,
            )
            statement = statement.on_conflict_do_update(
                index_elements=[table.c.bucket_key, table.c.window_start],
                set_={"count": table.c.count + 1},
            ).returning(table.c.count)
            counts.append(db.execute(statement).scalar_one())
        db.execute(delete(table).where(table.c.window_start < window_start))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("CDN upload rate limit could not be recorded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload rate limiting is temporarily unavailable",
        ) from exc

    if any(count > limit for count in counts):
        retry_after = window_seconds - (current_time % window_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def promote_temp_file(
    temp_path: str,
    target_folder: str,
) -> dict[str, Any]:
    target_folder = _validate_folder(target_folder, allow_temp=False)
    temp_path = _validate_relative_path(temp_path)

    if not temp_path.startswith(f"{TEMP_FOLDER}/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only temporary CDN files can be promoted",
        )

    filename = temp_path.removeprefix(f"{TEMP_FOLDER}/")
    if "/" in filename or not _TEMP_FILENAME_RE.fullmatch(filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only server-generated temporary files can be promoted",
        )

    source = _resolve_path(temp_path)

    try:
        source_info = source.lstat()
        resolved_source = source.resolve(strict=True)
    except FileNotFoundError:
        source_info = None
        resolved_source = None
    if (
        source_info is None
        or not stat.S_ISREG(source_info.st_mode)
        or resolved_source is None
        or (resolved_source != CDN_ROOT and CDN_ROOT not in resolved_source.parents)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary file not found",
        )

    destination_relative_path = f"{target_folder}/{filename}"
    destination = _resolve_path(destination_relative_path)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Destination file already exists",
        )

    try:
        source_fd = os.open(
            source,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary file not found",
        ) from None
    try:
        opened_source = os.fstat(source_fd)
        if (
            not stat.S_ISREG(opened_source.st_mode)
            or (opened_source.st_dev, opened_source.st_ino)
            != (source_info.st_dev, source_info.st_ino)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporary file is not a regular file",
            )
        try:
            os.link(source, destination, follow_symlinks=False)
        except FileExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Destination file already exists",
            ) from None
        linked_file = destination.lstat()
        if (
            not stat.S_ISREG(linked_file.st_mode)
            or (linked_file.st_dev, linked_file.st_ino)
            != (opened_source.st_dev, opened_source.st_ino)
        ):
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporary file changed during promotion",
            )
        expected_identity = (opened_source.st_dev, opened_source.st_ino)
    finally:
        os.close(source_fd)

    try:
        current_source = source.lstat()
        if (
            not stat.S_ISREG(current_source.st_mode)
            or (current_source.st_dev, current_source.st_ino) != expected_identity
        ):
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Temporary file changed during promotion",
            )
        source.unlink()
    except OSError:
        destination.unlink(missing_ok=True)
        raise

    return {
        "path": destination_relative_path,
        "url": (
            build_cdn_url(destination_relative_path)
            if target_folder in PUBLIC_FOLDERS
            else ""
        ),
        "filename": filename,
        "bytes": destination.stat().st_size,
    }


def delete_cdn_file(relative_path: str) -> bool:
    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if (
        len(parts) != 2
        or parts[0] not in PUBLIC_FOLDERS | {TEMP_FOLDER}
        or not _TEMP_FILENAME_RE.fullmatch(parts[1])
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only generated CDN files can be deleted",
        )

    path = _resolve_path(relative_path)
    try:
        file_stat = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(file_stat.st_mode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only regular CDN files can be deleted",
        )

    path.unlink()
    return True


def cleanup_expired_temp_uploads() -> int:
    cutoff = time.time() - TEMP_UPLOAD_RETENTION_SECONDS
    temp_directory = CDN_ROOT / TEMP_FOLDER
    deleted_count = 0

    try:
        directory_info = temp_directory.lstat()
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or not temp_directory.resolve().is_relative_to(CDN_ROOT)
        ):
            raise OSError("Temporary upload directory is unsafe")
        entries = temp_directory.iterdir()
        for entry in entries:
            try:
                entry_stat = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(entry_stat.st_mode) and entry_stat.st_mtime <= cutoff:
                    entry.unlink()
                    deleted_count += 1
            except OSError:
                logger.exception("Could not clean expired temporary CDN file: %s", entry)
    except OSError:
        logger.exception("Could not access temporary CDN upload directory: %s", temp_directory)

    staging_root = CDN_ROOT / ".upload-staging"
    staging_deleted = 0
    try:
        try:
            staging_info = staging_root.lstat()
        except FileNotFoundError:
            staging_info = None
        if staging_info is not None:
            if (
                not stat.S_ISDIR(staging_info.st_mode)
                or not staging_root.resolve().is_relative_to(CDN_ROOT)
            ):
                raise OSError("Staging directory is unsafe")
            for entry in staging_root.iterdir():
                try:
                    entry_stat = entry.lstat()
                    if (
                        entry.name.startswith("upload-")
                        and stat.S_ISDIR(entry_stat.st_mode)
                        and entry_stat.st_mtime <= cutoff
                        and entry.resolve().is_relative_to(staging_root.resolve())
                    ):
                        shutil.rmtree(entry)
                        staging_deleted += 1
                except OSError:
                    logger.exception("Could not clean expired CDN staging directory: %s", entry)
    except OSError:
        logger.exception("Could not access CDN staging directory: %s", staging_root)
    if staging_deleted:
        logger.info("Removed %d expired CDN staging directories", staging_deleted)

    return deleted_count


def get_temporary_upload_path(filename: str) -> Path:
    if not _TEMP_FILENAME_RE.fullmatch(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary upload not found",
        )
    path = _resolve_path(f"{TEMP_FOLDER}/{filename}")
    try:
        file_stat = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary upload not found",
        ) from None
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or file_stat.st_nlink != 1
        or resolved.parent != (CDN_ROOT / TEMP_FOLDER).resolve()
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary upload not found",
        )
    return path


def get_private_document_path(relative_path: str) -> Path:
    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if (
        len(parts) != 3
        or "/".join(parts[:2]) not in PRIVATE_DOCUMENT_FOLDERS
        or not _TEMP_FILENAME_RE.fullmatch(parts[2])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    path = _resolve_path(relative_path)
    private_root = (CDN_ROOT / "private").resolve()
    try:
        file_stat = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from None
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or file_stat.st_nlink != 1
        or resolved == private_root
        or private_root not in resolved.parents
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return path


def get_cdn_file_path(relative_path: str) -> Path:
    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if len(parts) < 2 or parts[0] not in PUBLIC_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CDN file not found",
        )
    path = _resolve_path(relative_path)
    try:
        file_stat = path.lstat()
    except OSError:
        file_stat = None
    if file_stat is None or not stat.S_ISREG(file_stat.st_mode):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CDN file not found",
        )

    return path


def build_cdn_url(relative_path: str) -> str:
    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if len(parts) < 2 or parts[0] not in PUBLIC_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only permanent public assets have CDN URLs",
        )
    return f"{CDN_BASE_URL}/{relative_path}"


def build_temporary_download_url(relative_path: str) -> str:
    relative_path = _validate_relative_path(relative_path)
    parts = relative_path.split("/")
    if (
        len(parts) != 2
        or parts[0] != TEMP_FOLDER
        or not _TEMP_FILENAME_RE.fullmatch(parts[1])
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid temporary upload path",
        )
    return f"/api/v1/public/files/temporary/{parts[1]}"