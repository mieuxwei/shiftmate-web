from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Connection

from backend.app.core.database import user_connection
from backend.app.repositories.pay_rates import (
    PayRateRepository,
    PostgresPayRateRepository,
)
from backend.app.schemas.pay_rates import (
    PayRateCreateRequest,
    PayRateResponse,
    PayRateUpdateRequest,
)
from backend.app.services.pay_rates import (
    CreatePayRateCommand,
    PayRateInUseError,
    PayRateOverlapError,
    PayRateRecordNotFoundError,
    PayRateService,
    PayRateServiceError,
    UpdatePayRateCommand,
)
from backend.app.services.shifts import ProfileNotFoundError

router = APIRouter(prefix="/pay-rates", tags=["pay-rates"])


@lru_cache
def get_pay_rate_repository() -> PostgresPayRateRepository:
    return PostgresPayRateRepository()


def get_pay_rate_service(
    repository: Annotated[PayRateRepository, Depends(get_pay_rate_repository)],
) -> PayRateService:
    return PayRateService(repository)


@router.get("", response_model=list[PayRateResponse])
def list_pay_rates(
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PayRateService, Depends(get_pay_rate_service)],
) -> list[PayRateResponse]:
    return [
        PayRateResponse.model_validate(record)
        for record in service.list_pay_rates(connection)
    ]


@router.post("", response_model=PayRateResponse, status_code=status.HTTP_201_CREATED)
def create_pay_rate(
    payload: PayRateCreateRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PayRateService, Depends(get_pay_rate_service)],
) -> PayRateResponse:
    try:
        record = service.create_pay_rate(
            connection,
            CreatePayRateCommand(
                hourly_rate=payload.hourly_rate,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
            ),
        )
    except ProfileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PayRateOverlapError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except PayRateServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return PayRateResponse.model_validate(record)


@router.patch("/{pay_rate_id}", response_model=PayRateResponse)
def update_pay_rate(
    pay_rate_id: UUID,
    payload: PayRateUpdateRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PayRateService, Depends(get_pay_rate_service)],
) -> PayRateResponse:
    try:
        record = service.update_pay_rate(
            connection,
            pay_rate_id,
            UpdatePayRateCommand(
                hourly_rate=payload.hourly_rate,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                effective_to_supplied="effective_to" in payload.model_fields_set,
            ),
        )
    except PayRateRecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (PayRateOverlapError, PayRateInUseError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except PayRateServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return PayRateResponse.model_validate(record)


@router.delete("/{pay_rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pay_rate(
    pay_rate_id: UUID,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PayRateService, Depends(get_pay_rate_service)],
) -> Response:
    try:
        service.delete_pay_rate(connection, pay_rate_id)
    except PayRateRecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PayRateInUseError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
