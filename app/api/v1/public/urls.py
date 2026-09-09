from fastapi import APIRouter

from app.api.v1.public.destinations import router as destinations_router
from app.api.v1.public.uploads import router as uploads_router

router = APIRouter()

router.include_router(uploads_router)
router.include_router(destinations_router)
