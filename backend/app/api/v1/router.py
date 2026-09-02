from fastapi import APIRouter

from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.assistant import router as assistant_router
from backend.app.api.v1.calendar import router as calendar_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.imports import router as imports_router
from backend.app.api.v1.pay_rates import router as pay_rates_router
from backend.app.api.v1.policies import router as policies_router
from backend.app.api.v1.shifts import router as shifts_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analytics_router)
api_router.include_router(health_router)
api_router.include_router(imports_router)
api_router.include_router(pay_rates_router)
api_router.include_router(policies_router)
api_router.include_router(assistant_router)
api_router.include_router(calendar_router)
api_router.include_router(shifts_router)
