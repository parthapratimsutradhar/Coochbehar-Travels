import asyncio
import copy
import logging
from datetime import datetime

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.middleware.upload_request_limit import UploadRequestSizeLimitMiddleware
from app.api.v1.admin.urls import router as admin_router
from app.api.v1.enduser.urls import router as enduser_router
from app.api.v1.public.urls import router as public_router
from app.api.v1.shared.urls import router as shared_router
# IMPORTANT: socket_manager MUST be imported before any module that imports
# socket_service, to ensure event handlers are registered on sio first.
from app.realtime.socket_manager import sio  # noqa: E402
import socketio

logger = logging.getLogger(__name__)

# ── Scheduled data cleanup ────────────────────────────────────────────
async def _scheduled_cleanup_task(
    job_name: str,
    cleanup,
    interval_days: int,
    hour: int,
    minute: int,
) -> None:
    """Keep one configured cleanup job scheduled while the app is running."""
    from app.services.cleanup_service import next_cleanup_run

    while True:
        try:
            scheduled_time = next_cleanup_run(interval_days, hour, minute)
            delay = max(
                (scheduled_time - datetime.now(scheduled_time.tzinfo)).total_seconds(),
                0,
            )
            logger.info("Next %s scheduled for %s", job_name, scheduled_time.isoformat())
            await asyncio.sleep(delay)
            summary = await cleanup()
            logger.info("%s completed: %s", job_name, summary)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Scheduled %s task error", job_name)
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.cdn_service import check_antivirus_available

    if settings.CDN_ANTIVIRUS_ENABLED:
        scanner_available = await asyncio.to_thread(check_antivirus_available)
        if scanner_available:
            logger.info("CDN antivirus scanner is available")
        else:
            logger.error("CDN antivirus is enabled but the scanner is unavailable")

    from app.services.cleanup_service import run_analytics_cleanup, run_cleanup

    tasks = [
        asyncio.create_task(
            _scheduled_cleanup_task(
                "analytics cleanup",
                run_analytics_cleanup,
                settings.ANALYTICS_CLEANUP_INTERVAL_DAYS,
                settings.ANALYTICS_CLEANUP_HOUR,
                settings.ANALYTICS_CLEANUP_MINUTE,
            )
        ),
        asyncio.create_task(
            _scheduled_cleanup_task(
                "temporary CDN cleanup",
                run_cleanup,
                settings.CDN_CLEANUP_INTERVAL_DAYS,
                settings.CDN_CLEANUP_HOUR,
                settings.CDN_CLEANUP_MINUTE,
            )
        ),
    ]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    title="Coochbehar Travels API",
    description="Tour Marketing, Visitor Analytics & Lead Generation System",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(UploadRequestSizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


# ── API routers ───────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"

app.include_router(shared_router, prefix=API_V1_PREFIX)
app.include_router(admin_router, prefix=API_V1_PREFIX)
app.include_router(enduser_router, prefix=API_V1_PREFIX)
app.include_router(public_router, prefix=API_V1_PREFIX)




# ── Filtered OpenAPI helpers ──────────────────────────────────────────
def _filter_schema(
    full_schema: dict,
    *,
    title: str,
    description: str,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    exclude_exact: set[str] | None = None,
) -> dict:
    """Return a deep-copy of *full_schema* with paths filtered.

    * If *include* is given, only paths starting with any of those prefixes
      are kept.
    * If *exclude* is given, paths starting with any of those prefixes are
      removed.
    * If *exclude_exact* is given, paths matching exactly are removed.
    * All may be combined (include is applied first).
    """
    schema = copy.deepcopy(full_schema)
    schema["info"]["title"] = title
    schema["info"]["description"] = description

    paths = full_schema.get("paths", {})
    if include is not None:
        paths = {
            p: d for p, d in paths.items()
            if any(p.startswith(pfx) for pfx in include)
        }
    if exclude is not None:
        paths = {
            p: d for p, d in paths.items()
            if not any(p.startswith(pfx) for pfx in exclude)
        }
    if exclude_exact is not None:
        paths = {
            p: d for p, d in paths.items()
            if p not in exclude_exact
        }
    schema["paths"] = paths

    # Prune unused tags
    used_tags: set[str] = set()
    for path_data in schema["paths"].values():
        for op in path_data.values():
            if isinstance(op, dict) and "tags" in op:
                used_tags.update(op["tags"])
    if "tags" in schema:
        schema["tags"] = [t for t in schema["tags"] if t.get("name") in used_tags]

    return schema


def _enduser_openapi() -> dict:
    return _filter_schema(
        fastapi_app.openapi(),
        title="Coochbehar Travels — Enduser API",
        description="Customer-facing APIs.",
        include={
            "/api/v1/auth",
            "/api/v1/account",
            "/api/v1/tour-packages",
            "/api/v1/rules-regulations",
            "/api/v1/hotels",
            "/api/v1/vehicles",
            "/api/v1/destinations",
            "/api/v1/enquiries",
            "/api/v1/visitors",
            "/api/v1/customer-tours",
            "/api/v1/review",
            "/api/v1/wishlist",
            "/api/v1/documents",
            "/api/v1/referral",
            "/api/v1/quotations",
            "/api/v1/transactions",
            "/api/v1/sessions",
            "/api/v1/notifications",
            "/api/v1/enums",
        },
    )


def _admin_openapi() -> dict:
    return _filter_schema(
        fastapi_app.openapi(),
        title="Coochbehar Travels — Admin API",
        description="Administrative APIs.",
        include={
            "/api/v1/admin",
            "/api/v1/sessions",
            "/api/v1/notifications",
            "/api/v1/enums",
        },
    )


def _public_openapi() -> dict:
    return _filter_schema(
        fastapi_app.openapi(),
        title="Coochbehar Travels — Public API",
        description="Public APIs.",
        include={
            "/api/v1/public/files",
            "/api/v1/public/ranking",
        },
    )


# ── OpenAPI JSON endpoints ────────────────────────────────────────────
@app.get("/openapi/enduser.json", include_in_schema=False)
async def enduser_openapi_json():
    return JSONResponse(_enduser_openapi())


@app.get("/openapi/admin.json", include_in_schema=False)
async def admin_openapi_json():
    return JSONResponse(_admin_openapi())


@app.get("/openapi/public.json", include_in_schema=False)
async def public_openapi_json():
    return JSONResponse(_public_openapi())


# ── Scalar documentation pages ────────────────────────────────────────
@app.get("/docs", include_in_schema=False)
@app.get("/scalar", include_in_schema=False)
async def enduser_docs():
    return get_scalar_api_reference(
        openapi_url="/openapi/enduser.json",
        title="Coochbehar Travels — Enduser API Documentation",
    )


@app.get("/admin/docs", include_in_schema=False)
async def admin_docs():
    return get_scalar_api_reference(
        openapi_url="/openapi/admin.json",
        title="Coochbehar Travels — Admin API Documentation",
    )


@app.get("/public/docs", include_in_schema=False)
async def public_docs():
    return get_scalar_api_reference(
        openapi_url="/openapi/public.json",
        title="Coochbehar Travels — Public API Documentation",
    )


# ── Health check ──────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def read_root():
    from app.services.cdn_service import antivirus_health_status

    return {
        "status": "online",
        "service": "Coochbehar Travels API",
        "upload_antivirus": antivirus_health_status(),
        "documentation": {
            "enduser": "/docs",
            "admin": "/admin/docs",
            "public": "/public/docs",
        },
    }


# Keep the FastAPI reference for OpenAPI generation after the public ASGI
# application name is replaced with the Socket.IO wrapper below.
fastapi_app = app

# Socket.IO wraps the completed FastAPI application so its default
# `/socket.io/` endpoint is matched before requests are delegated to FastAPI.
# Mounting ASGIApp at the same `/socket.io` path can strip that prefix before
# python-socketio receives the scope and prevent the handshake from matching.
app = socketio.ASGIApp(sio, other_asgi_app=app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)