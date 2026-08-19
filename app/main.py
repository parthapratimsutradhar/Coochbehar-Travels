import copy

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.core.config import settings
from app.api.v1.admin.auth import router as admin_auth_router
from app.api.v1.admin.enquiries import router as admin_enquiries_router
from app.api.v1.admin.leads import router as admin_leads_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.enduser.auth import router as enduser_auth_router
from app.api.v1.enduser.enquiries import router as enquiries_router
from app.api.v1.enduser.tour_packages import router as tour_packages_router
from app.api.v1.enduser.visitors import router as visitors_router
from app.api.v1.public.uploads import router as uploads_router

app = FastAPI(
    title="Coochbehar Travels API",
    description="Tour Marketing, Visitor Analytics & Lead Generation System",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ───────────────────────────────────────────────────────
app.include_router(sessions_router, prefix="/api/v1")  # /api/v1/sessions/*
app.include_router(admin_auth_router, prefix="/api/v1")  # /api/v1/admin/auth/otp/*
app.include_router(enduser_auth_router, prefix="/api/v1")  # /api/v1/enduser/auth/otp/*
app.include_router(tour_packages_router, prefix="/api/v1")
app.include_router(enquiries_router, prefix="/api/v1")
app.include_router(visitors_router, prefix="/api/v1")
app.include_router(admin_leads_router, prefix="/api/v1")
app.include_router(admin_enquiries_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")


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
    """Enduser docs: /api/v1/enduser/*, public enduser routes, and shared sessions."""
    full = app.openapi()
    return _filter_schema(
        full,
        title="Coochbehar Travels — Enduser API",
        description="Customer-facing APIs: Customer Auth, Tour Packages, Enquiries, Visitors, Telemetry & Session Management.",
        include={
            "/api/v1/enduser",
            "/api/v1/tour-packages",
            "/api/v1/enquiries",
            "/api/v1/visitors",
            "/api/v1/sessions",
        },
    )


def _admin_openapi() -> dict:
    """Admin docs: /api/v1/admin/* routes and shared sessions."""
    full = app.openapi()
    return _filter_schema(
        full,
        title="Coochbehar Travels — Admin API",
        description="Administrative APIs: Staff Auth, Sales Leads Pipeline, Enquiry Management & Session Management.",
        include={
            "/api/v1/admin",
            "/api/v1/sessions",
        },
    )


def _public_openapi() -> dict:
    """Public/shared docs: file uploads."""
    full = app.openapi()
    return _filter_schema(
        full,
        title="Coochbehar Travels — Public API",
        description="Shared APIs: File Uploads.",
        include={
            "/api/v1/public/files",
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
    return {
        "status": "online",
        "service": "Coochbehar Travels API",
        "documentation": {
            "enduser": "/docs",
            "admin": "/admin/docs",
            "public": "/public/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
