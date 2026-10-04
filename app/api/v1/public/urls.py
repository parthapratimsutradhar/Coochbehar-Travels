from fastapi import APIRouter

from app.api.v1.public.uploads import router as uploads_router
from app.api.v1.public.ranking import router as ranking_router

router = APIRouter()

router.include_router(uploads_router)
router.include_router(ranking_router)
