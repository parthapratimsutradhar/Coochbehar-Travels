from collections.abc import Awaitable, Callable
from typing import Any

from starlette.responses import JSONResponse

from app.core.config import settings


class _UploadRequestTooLarge(Exception):
    pass


class UploadRequestSizeLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/v1/public/files/upload"
        ):
            await self.app(scope, receive, send)
            return

        max_file_bytes = max(
            settings.CDN_MAX_IMAGE_SIZE_MB,
            settings.CDN_MAX_VIDEO_SIZE_MB,
            settings.CDN_MAX_PDF_SIZE_MB,
        ) * 1024 * 1024
        max_request_bytes = max_file_bytes + 256 * 1024
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared_length = int(content_length)
            except ValueError:
                response = JSONResponse(
                    {"detail": "Invalid upload request size"},
                    status_code=400,
                )
                await response(scope, receive, send)
                return
            if declared_length > max_request_bytes:
                response = JSONResponse(
                    {"detail": "Upload request exceeds the configured size limit"},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def receive_with_limit():
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > max_request_bytes:
                    raise _UploadRequestTooLarge
            return message

        try:
            await self.app(scope, receive_with_limit, send)
        except _UploadRequestTooLarge:
            response = JSONResponse(
                {"detail": "Upload request exceeds the configured size limit"},
                status_code=413,
            )
            await response(scope, receive, send)