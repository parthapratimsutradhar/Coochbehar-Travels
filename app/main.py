from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.api.v1.admin.enquiries import router as admin_enquiries_router
from app.api.v1.admin.leads import router as admin_leads_router
from app.api.v1.enduser.enquiries import router as enquiries_router
from app.api.v1.enduser.tour_packages import router as tour_packages_router
from app.api.v1.enduser.visitors import router as visitors_router

app = FastAPI(
    title="Coochbehar Travels API",
    description="Tour Marketing, Visitor Analytics & Lead Generation System",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# ── API v1 routers ───────────────────────────────────────────────────
app.include_router(tour_packages_router, prefix="/api/v1")
app.include_router(enquiries_router, prefix="/api/v1")
app.include_router(visitors_router, prefix="/api/v1")
app.include_router(admin_leads_router, prefix="/api/v1")
app.include_router(admin_enquiries_router, prefix="/api/v1")



@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "online",
        "service": "Coochbehar Travels API",
        "documentation": "/docs",
    }


@app.get("/docs", include_in_schema=False)
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title + " - Scalar API Documentation",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

