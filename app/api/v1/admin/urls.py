from fastapi import APIRouter

from app.api.v1.admin.account import router as account_router
from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.enquiries import router as enquiries_router
from app.api.v1.admin.leads import router as leads_router
from app.api.v1.admin.documents import router as documents_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(account_router)
router.include_router(analytics_router)
router.include_router(leads_router)
router.include_router(documents_router)
router.include_router(enquiries_router)
