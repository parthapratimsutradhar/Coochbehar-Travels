from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse 
from app.core.messages.error import SystemError, ErrorCode


def _error_response(
    *,
    status_code: int,
    message: str,
    code: ErrorCode | str,
    details: object = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "error": {
                "code": code,
                "details": details,
            },
        },
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = ErrorCode.from_status_code(exc.status_code)
    message = str(exc.detail)
    details = None

    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", exc.detail.get("detail", str(exc.detail)))
        code = exc.detail.get("code", code)
        details = exc.detail.get("details")

    return _error_response(
        status_code=exc.status_code,
        message=message,
        code=code,
        details=details,
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = []
    for error in exc.errors():
        field_loc = [
            str(location)
            for location in error.get("loc", [])
            if location not in ("body", "query", "path", "header")
        ]
        details.append({
            "field": ".".join(field_loc) if field_loc else "request",
            "message": error.get("msg", "Invalid input"),
        })

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        message=SystemError.VALIDATION_FAILED,
        code=ErrorCode.VALIDATION_ERROR,
        details=details,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=SystemError.UNEXPECTED,
        code=ErrorCode.INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
