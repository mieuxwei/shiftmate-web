from fastapi import APIRouter

from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.pay_rates import router as pay_rates_router
from backend.app.api.v1.shifts import router as shifts_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analytics_router)
api_router.include_router(health_router)
api_router.include_router(pay_rates_router)
api_router.include_router(shifts_router)
