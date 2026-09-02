from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.core.settings import Settings, get_settings
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(environment=settings.app_env)
