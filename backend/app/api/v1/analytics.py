from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection

from backend.app.api.v1.pay_rates import get_pay_rate_repository
from backend.app.api.v1.shifts import get_shift_repository
from backend.app.core.database import user_connection
from backend.app.repositories.pay_rates import PayRateRepository
from backend.app.repositories.profiles import (
    PostgresProfileRepository,
    ProfileRepository,
)
from backend.app.repositories.shifts import ShiftRepository
from backend.app.schemas.analytics import AnalyticsSummaryResponse
from backend.app.services.analytics import (
    AnalyticsCalculationError,
    AnalyticsService,
    AnalyticsServiceError,
)
from backend.app.services.shifts import ProfileNotFoundError

router = APIRouter(prefix="/analytics", tags=["analytics"])


@lru_cache
def get_profile_repository() -> PostgresProfileRepository:
    return PostgresProfileRepository()


def get_analytics_service(
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    shift_repository: Annotated[ShiftRepository, Depends(get_shift_repository)],
    pay_rate_repository: Annotated[PayRateRepository, Depends(get_pay_rate_repository)],
) -> AnalyticsService:
    return AnalyticsService(profile_repository, shift_repository, pay_rate_repository)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AnalyticsSummaryResponse:
    try:
        summary = service.get_summary(connection, date_from, date_to)
    except ProfileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AnalyticsCalculationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AnalyticsServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return AnalyticsSummaryResponse.model_validate(summary)
