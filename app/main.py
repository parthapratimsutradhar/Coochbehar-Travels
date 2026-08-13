from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

app = FastAPI(
    title="Coochbehar Travels API",
    description="Tour Marketing, Visitor Analytics & Lead Generation System",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)


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

