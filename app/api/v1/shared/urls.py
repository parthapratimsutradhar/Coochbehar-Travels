from fastapi import APIRouter

from app.api.v1.shared.sessions import router as sessions_router
from app.api.v1.shared.notifications import router as notifications_router

router = APIRouter()

router.include_router(sessions_router)
router.include_router(notifications_router)
