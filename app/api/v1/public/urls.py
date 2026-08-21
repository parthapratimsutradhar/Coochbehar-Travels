from fastapi import APIRouter

from app.api.v1.public.uploads import router as uploads_router

router = APIRouter()

router.include_router(uploads_router)
