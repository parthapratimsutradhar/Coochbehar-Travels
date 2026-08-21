from fastapi import APIRouter

from app.api.v1.shared.sessions import router as sessions_router

router = APIRouter()

router.include_router(sessions_router)
