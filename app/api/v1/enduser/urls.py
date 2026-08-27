from fastapi import APIRouter

from app.api.v1.enduser.auth import router as auth_router
from app.api.v1.enduser.account import router as account_router
from app.api.v1.enduser.customer_tour import router as customer_tour_router
from app.api.v1.enduser.document import router as document_router
from app.api.v1.enduser.enquiries import router as enquiries_router
from app.api.v1.enduser.review import router as review_router
from app.api.v1.enduser.referral import router as referral_router
from app.api.v1.enduser.tour_packages import router as tour_packages_router
from app.api.v1.enduser.visitors import router as visitors_router
from app.api.v1.enduser.wishlist import router as wishlist_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(account_router)
router.include_router(customer_tour_router)
router.include_router(document_router)
router.include_router(tour_packages_router)
router.include_router(enquiries_router)
router.include_router(review_router)
router.include_router(referral_router)
router.include_router(visitors_router)
router.include_router(wishlist_router)
