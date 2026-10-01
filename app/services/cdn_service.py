from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


CDN_ROOT = Path(settings.CDN_STORAGE_PATH).resolve()
CDN_BASE_URL = settings.CDN_BASE_URL.rstrip("/")

TEMP_FOLDER = "temporary-uploads"

PERMANENT_FOLDERS = {
    "profile-picture",
    "tour-packages",
    "customer-documents",
    "admin-documents",
    "review-gallery",
    "destination-images",
    "hotel-images",
    "vehicle-images",
    "room-images",
}

ALLOWED_FOLDERS = PERMANENT_FOLDERS | {TEMP_FOLDER}

CDN_ROOT.mkdir(parents=True, exist_ok=True)

for folder in ALLOWED_FOLDERS:
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


def _validate_folder(folder: str, *, allow_temp: bool = True) -> str:
    folder = folder.strip().strip("/")

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
    extension = ALLOWED_CONTENT_TYPES.get(content_type)

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    return extension


def _validate_size(content: bytes, content_type: str) -> None:
    if content_type.startswith("image/"):
        max_size = MAX_IMAGE_SIZE
    elif content_type.startswith("video/"):
        max_size = MAX_VIDEO_SIZE
    elif content_type == "application/pdf":
        max_size = MAX_PDF_SIZE
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {max_size // (1024 * 1024)} MB limit",
        )


def _resolve_path(relative_path: str) -> Path:
    relative_path = relative_path.strip().lstrip("/")
    path = (CDN_ROOT / relative_path).resolve()

    if path != CDN_ROOT and CDN_ROOT not in path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CDN file path",
        )

    return path


def _validate_relative_path(relative_path: str) -> str:
    path = relative_path.strip().replace("\\", "/").lstrip("/")

    if not path or path.startswith("../") or "/../" in path or path.endswith("/.."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CDN file path",
        )

    return path


async def upload_file_to_cdn(file: UploadFile) -> dict[str, Any]:
    content_type = (file.content_type or "").lower()
    extension = _validate_content_type(content_type)

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )

    _validate_size(content, content_type)

    filename = f"{uuid4().hex}{extension}"
    relative_path = f"{TEMP_FOLDER}/{filename}"
    destination = _resolve_path(relative_path)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return {
        "path": relative_path,
        "url": f"{CDN_BASE_URL}/{relative_path}",
        "filename": filename,
        "content_type": content_type,
        "bytes": len(content),
    }


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

    source = _resolve_path(temp_path)

    if not source.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Temporary file not found",
        )

    filename = source.name
    destination_relative_path = f"{target_folder}/{filename}"
    destination = _resolve_path(destination_relative_path)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Destination file already exists",
        )

    source.replace(destination)

    return {
        "path": destination_relative_path,
        "url": f"{CDN_BASE_URL}/{destination_relative_path}",
        "filename": filename,
        "bytes": destination.stat().st_size,
    }


def delete_cdn_file(relative_path: str) -> bool:
    relative_path = _validate_relative_path(relative_path)

    if relative_path.startswith(f"{TEMP_FOLDER}/"):
        path = _resolve_path(relative_path)
    else:
        path = _resolve_path(relative_path)

    if not path.is_file():
        return False

    path.unlink()
    return True


def get_cdn_file_path(relative_path: str) -> Path:
    relative_path = _validate_relative_path(relative_path)
    path = _resolve_path(relative_path)

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CDN file not found",
        )

    return path


def build_cdn_url(relative_path: str) -> str:
    relative_path = _validate_relative_path(relative_path)
    return f"{CDN_BASE_URL}/{relative_path}"