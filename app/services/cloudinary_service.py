import hashlib
from io import BytesIO
import re
import time
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


CLOUDINARY_ROOT_FOLDER = "Coochbehar-travels"
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/mov",
    "video/webm",
    "application/pdf",
}

UPLOAD_ALLOWED_FOLDERS = {
    "profile-picture",
    "tour-packages",
    "temporary-uploads",
    "review-gallery"
}

UPLOAD_IMAGE_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_VIDEO_MAX_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_VIDEO_MAX_DURATION = 60            # seconds
UPLOAD_RATE_LIMIT_PER_HOUR = 10
GOOGLE_IMAGE_HOST_SUFFIX = ".googleusercontent.com"


def _clean_folder_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return segment.strip("-")


def build_cloudinary_folder(sub_folder: str) -> str:
    parts = [
        _clean_folder_segment(part)
        for part in re.split(r"[\\/]+", sub_folder)
        if _clean_folder_segment(part)
    ]
    if not parts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="sub_folder must contain at least one valid folder name",
        )
    return "/".join([CLOUDINARY_ROOT_FOLDER, *parts])


def _validate_upload(file: UploadFile, content: bytes, sub_folder: str) -> str:
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Uploaded file is empty",
        )
    max_size = (
        UPLOAD_VIDEO_MAX_SIZE
        if file.content_type and file.content_type.startswith("video/")
        else UPLOAD_IMAGE_MAX_SIZE
    )
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            message=f"Uploaded file exceeds the {max_size // (1024 * 1024)} MB limit",
        )
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            message="Unsupported file type",
        )

    folder_name = sub_folder.strip().replace("\\", "/").split("/", 1)[0]
    if folder_name not in UPLOAD_ALLOWED_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Unsupported upload folder",
        )
    return build_cloudinary_folder(sub_folder)


def _sign_upload_params(params: dict[str, Any]) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{settings.CLOUDINARY_API_SECRET}".encode("utf-8")).hexdigest()


def _validate_image_content(content: bytes, content_type: str) -> None:
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Google profile picture is not an image",
        )

    try:
        from PIL import Image, UnidentifiedImageError

        with Image.open(BytesIO(content)) as image:
            image.verify()
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image safety scanner is not installed",
        ) from exc
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture is not a valid safe image",
        ) from exc


def _validate_google_picture_url(picture_url: str) -> None:
    try:
        parsed = httpx.URL(picture_url)
    except httpx.InvalidURL as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture URL is invalid",
        ) from exc
    if parsed.scheme != "https" or not parsed.host:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture URL is invalid",
        )
    if not (parsed.host == "googleusercontent.com" or parsed.host.endswith(GOOGLE_IMAGE_HOST_SUFFIX)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google profile picture must come from Google",
        )


async def upload_content_to_cloudinary(
    content: bytes,
    filename: str,
    content_type: str,
    sub_folder: str,
) -> dict[str, Any]:
    if not (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Cloudinary is not configured",
        )
    if settings.CLOUDINARY_API_SECRET == settings.CLOUDINARY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Cloudinary API secret is invalid. Set CLOUDINARY_API_SECRET to the hidden API Secret from your Cloudinary dashboard, not the API Key.",
        )

    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )
    folder = _validate_upload(file, content, sub_folder)
    timestamp = int(time.time())
    upload_params = {
        "folder": folder,
        "timestamp": timestamp,
    }
    signature = _sign_upload_params(upload_params)

    data = {
        **upload_params,
        "api_key": settings.CLOUDINARY_API_KEY,
        "signature": signature,
    }
    files = {
        "file": (
            file.filename or "upload",
            content,
            file.content_type or "application/octet-stream",
        )
    }
    upload_url = (
        f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/auto/upload"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(upload_url, data=data, files=files)

    if response.status_code >= 400:
        try:
            error = response.json().get("error", {}).get("message")
        except ValueError:
            error = response.text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=f"Cloudinary upload failed: {error or 'unknown error'}",
        )

    result = response.json()
    result["folder"] = folder
    return result


async def upload_file_to_cloudinary(file: UploadFile, sub_folder: str) -> dict[str, Any]:
    return await upload_content_to_cloudinary(
        content=await file.read(),
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        sub_folder=sub_folder,
    )


async def upload_google_profile_picture(picture_url: str) -> str:
    _validate_google_picture_url(picture_url)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.get(picture_url)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to download Google profile picture",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to download Google profile picture",
        )

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    content = response.content
    _validate_image_content(content, content_type)
    result = await upload_content_to_cloudinary(
        content=content,
        filename="google-profile-picture",
        content_type=content_type,
        sub_folder="profile-picture",
    )
    return result["secure_url"]
