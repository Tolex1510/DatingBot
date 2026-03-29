from fastapi import APIRouter

from app.api.v1.matches import router as matches_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.photos import router as photos_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(users_router)
router.include_router(profiles_router)
router.include_router(ratings_router)
router.include_router(matches_router)
router.include_router(photos_router)
router.include_router(metrics_router)
