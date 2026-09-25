import hashlib
import asyncio
import importlib
from io import BytesIO
import logging
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader
import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


CLOUDINARY_ROOT_FOLDER = "Coochbehar-travels"
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/avif",
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
    "customer-documents",
    "admin-documents",
    "review-gallery",
    "destination-images",
    "hotel-images",
    "vehicle-images",
    "room-images",
}

UPLOAD_IMAGE_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_VIDEO_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
UPLOAD_VIDEO_MAX_DURATION = 60            # seconds
UPLOAD_RATE_LIMIT_PER_HOUR = 10
GOOGLE_IMAGE_HOST_SUFFIX = ".googleusercontent.com"

# A small Render instance cannot safely process multiple large uploads at once.
# Serializing this resource-intensive section keeps concurrent requests from
# multiplying the peak memory used by image/PIL and video/FFmpeg processing.
_UPLOAD_CONCURRENCY = asyncio.Semaphore(1)


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
            detail="sub_folder must contain at least one valid folder name",
        )
    return "/".join([CLOUDINARY_ROOT_FOLDER, *parts])


def _validate_upload(
    content: bytes,
    content_type: str,
    sub_folder: str,
) -> str:
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    max_size = (
        UPLOAD_VIDEO_MAX_SIZE
        if content_type.startswith("video/")
        else UPLOAD_IMAGE_MAX_SIZE
    )
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds the {max_size // (1024 * 1024)} MB limit",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    folder_name = sub_folder.strip().replace("\\", "/").split("/", 1)[0]
    if folder_name not in UPLOAD_ALLOWED_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported upload folder",
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


def _compress_image(content: bytes, content_type: str) -> bytes:
    from PIL import Image

    with Image.open(BytesIO(content)) as image:
        if getattr(image, "is_animated", False):
            return content
        output = BytesIO()
        if content_type == "image/jpeg":
            image.convert("RGB").save(
                output,
                format="JPEG",
                quality=95,
                optimize=True,
                progressive=True,
            )
        elif content_type == "image/png":
            image.save(output, format="PNG", optimize=True)
        elif content_type == "image/webp":
            image.save(output, format="WEBP", quality=95, method=6)
        else:
            return content
        compressed = output.getvalue()
    return compressed if len(compressed) < len(content) else content

# NEEd to upgrade in production, too havy in render
def _compress_video(content: bytes, filename: str) -> tuple[bytes, str, str]:
    try:
        ffmpeg = importlib.import_module("imageio_ffmpeg").get_ffmpeg_exe()
    except ImportError:
        ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video compression requires FFmpeg to be installed on the server",
        )

    input_suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp4"
    with tempfile.TemporaryDirectory() as directory:
        input_path = f"{directory}/input{input_suffix}"
        output_path = f"{directory}/output.mp4"
        with open(input_path, "wb") as input_file:
            input_file.write(content)
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                input_path,
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                output_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded video could not be compressed",
            )
        with open(output_path, "rb") as output_file:
            compressed = output_file.read()

    if len(compressed) >= len(content):
        return content, filename, "video/mp4"
    return compressed, f"{filename.rsplit('.', 1)[0] if '.' in filename else filename}.mp4", "video/mp4"


async def _compress_upload(
    content: bytes,
    filename: str,
    content_type: str,
) -> tuple[bytes, str, str]:
    if content_type.startswith("image/"):
        return await asyncio.to_thread(
            _compress_image,
            content,
            content_type,
        ), filename, content_type

    if content_type.startswith("video/"):
        return content, filename, content_type

    return content, filename, content_type


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


async def _upload_content_to_cloudinary(
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
            detail="Cloudinary is not configured",
        )
    if settings.CLOUDINARY_API_SECRET == settings.CLOUDINARY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary API secret is invalid. Set CLOUDINARY_API_SECRET to the hidden API Secret from your Cloudinary dashboard, not the API Key.",
        )

    folder = _validate_upload(content, content_type, sub_folder)
    content, filename, content_type = await _compress_upload(content, filename, content_type)
    timestamp = int(time.time())
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")
    resource_type = "raw" if is_pdf else "auto"
    upload_params = {
        "access_mode": "public",
        "folder": folder,
        "public_id_prefix": folder,
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
            filename or "upload",
            content,
            content_type or "application/octet-stream",
        )
    }
    upload_url = (
        f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/{resource_type}/upload"
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
            detail=f"Cloudinary upload failed: {error or 'unknown error'}",
        )

    result = response.json()
    result["folder"] = folder
    return result


async def upload_content_to_cloudinary(
    content: bytes,
    filename: str,
    content_type: str,
    sub_folder: str,
) -> dict[str, Any]:
    async with _UPLOAD_CONCURRENCY:
        return await _upload_content_to_cloudinary(
            content=content,
            filename=filename,
            content_type=content_type,
            sub_folder=sub_folder,
        )


async def upload_file_to_cloudinary(file: UploadFile, sub_folder: str) -> dict[str, Any]:
    async with _UPLOAD_CONCURRENCY:
        return await _upload_content_to_cloudinary(
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


_CLOUDINARY_URL_PATTERN = re.compile(
    r"cloudinary\.com/[^/]+/(?P<resource_type>image|video|raw)/upload/(?:v\d+/)?(?P<public_id_with_ext>[^?#]+)"
)


def extract_cloudinary_asset_info(url_or_identifier: str | None) -> dict[str, str | None]:
    """
    Extracts public_id and resource_type from a Cloudinary URL or raw public_id.
    Returns:
        {
            "public_id": str | None,
            "resource_type": "image" | "video" | "raw" | None,
            "is_temporary": bool,
        }
    """
    if not url_or_identifier or not isinstance(url_or_identifier, str):
        return {"public_id": None, "resource_type": None, "is_temporary": False}

    cleaned = url_or_identifier.strip()
    match = _CLOUDINARY_URL_PATTERN.search(cleaned)
    if match:
        resource_type = match.group("resource_type")
        public_id_raw = match.group("public_id_with_ext")
        if resource_type in ("image", "video"):
            public_id = re.sub(r"\.[a-zA-Z0-9]+$", "", public_id_raw)
        else:
            public_id = public_id_raw
    elif cleaned.startswith(f"{CLOUDINARY_ROOT_FOLDER}/"):
        public_id = cleaned
        resource_type = None
    else:
        return {"public_id": None, "resource_type": None, "is_temporary": False}

    temp_prefix = f"{CLOUDINARY_ROOT_FOLDER}/temporary-uploads/"
    is_temporary = public_id.startswith(temp_prefix)
    return {
        "public_id": public_id,
        "resource_type": resource_type,
        "is_temporary": is_temporary,
    }


async def promote_cloudinary_asset(
    url_or_identifier: str | None,
    target_sub_folder: str,
    resource_type: str | None = None,
) -> dict[str, str]:
    """
    Promotes an asset from temporary-uploads to the target permanent folder.

    In Cloudinary Dynamic Folder mode:
    - asset_folder controls the Media Library folder
    - public_id controls the delivery URL

    Both are updated so the Media Library location and URL remain consistent.
    """
    if not url_or_identifier:
        return {"url": "", "public_id": ""}

    info = extract_cloudinary_asset_info(url_or_identifier)
    public_id = info["public_id"]

    if not public_id or not info["is_temporary"]:
        return {
            "url": url_or_identifier,
            "public_id": public_id or "",
        }

    temp_prefix = f"{CLOUDINARY_ROOT_FOLDER}/temporary-uploads/"
    relative_filename = public_id[len(temp_prefix):].lstrip("/")

    target_folder = build_cloudinary_folder(target_sub_folder)
    new_public_id = f"{target_folder}/{relative_filename}"
    resolved_resource_type = resource_type or info["resource_type"] or "image"

    try:
        # 1. Move the actual asset inside Cloudinary's Media Library.
        await asyncio.to_thread(
            cloudinary.uploader.explicit,
            public_id=public_id,
            type="upload",
            resource_type=resolved_resource_type,
            asset_folder=target_folder,
        )

        # 2. Change the public ID so the delivery URL also uses the
        #    permanent folder path.
        result = await asyncio.to_thread(
            cloudinary.uploader.rename,
            from_public_id=public_id,
            to_public_id=new_public_id,
            resource_type=resolved_resource_type,
            type="upload",
            overwrite=True,
        )

        return {
            "url": result.get("secure_url") or result.get("url") or url_or_identifier,
            "public_id": result.get("public_id") or new_public_id,
        }

    except Exception as exc:
        logger.exception(
            "Failed to promote Cloudinary asset %s to %s (%s): %s",
            public_id,
            new_public_id,
            resolved_resource_type,
            exc,
        )
        raise

