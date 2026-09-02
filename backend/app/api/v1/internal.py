from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import Engine

from backend.app.core.database import get_database_engine
from backend.app.core.internal_auth import (
    SchedulerPrincipal,
    require_scheduler_principal,
)
from backend.app.core.settings import Settings, get_settings
from backend.app.schemas.maintenance import MaintenanceResponse
from backend.app.services.maintenance import JOB_NAME, MaintenanceService

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/daily-maintenance", response_model=MaintenanceResponse)
def daily_maintenance(
    _: Annotated[SchedulerPrincipal, Depends(require_scheduler_principal)],
    schedule_time: Annotated[str, Header(alias="X-CloudScheduler-ScheduleTime")],
    job_name: Annotated[str, Header(alias="X-CloudScheduler-JobName")],
    engine: Annotated[Engine, Depends(get_database_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MaintenanceResponse:
    expected_job = settings.scheduler_job_name
    if expected_job != JOB_NAME or not (
        job_name == expected_job or job_name.endswith(f"/jobs/{expected_job}")
    ):
        raise HTTPException(status_code=403, detail="SCHEDULER_JOB_FORBIDDEN")
    try:
        scheduled_at = datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
        if scheduled_at.tzinfo is None:
            raise ValueError("timezone required")
        application_time = scheduled_at.astimezone(ZoneInfo(settings.app_timezone))
        logical_run_date = application_time.date()
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise HTTPException(status_code=422, detail="SCHEDULE_TIME_INVALID") from error
    result = MaintenanceService(engine, settings.database_maintenance_role).run(
        logical_run_date,
        settings.maintenance_draft_ttl_days,
        settings.maintenance_retention_days,
    )
    return MaintenanceResponse.model_validate(result, from_attributes=True)
