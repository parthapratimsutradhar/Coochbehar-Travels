import hashlib
import re
import time
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


CLOUDINARY_ROOT_FOLDER = "Coochbehar-travels"


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


def _sign_upload_params(params: dict[str, Any]) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{settings.CLOUDINARY_API_SECRET}".encode("utf-8")).hexdigest()


async def upload_file_to_cloudinary(file: UploadFile, sub_folder: str) -> dict[str, Any]:
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

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )

    folder = build_cloudinary_folder(sub_folder)
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
            detail=f"Cloudinary upload failed: {error or 'unknown error'}",
        )

    result = response.json()
    result["folder"] = folder
    return result
