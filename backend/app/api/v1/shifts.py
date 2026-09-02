from datetime import date
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Connection

from backend.app.core.database import user_connection
from backend.app.repositories.shifts import PostgresShiftRepository, ShiftRepository
from backend.app.schemas.shifts import (
    ShiftCreateRequest,
    ShiftResponse,
    ShiftUpdateRequest,
)
from backend.app.services.shifts import (
    CreateShiftCommand,
    ProfileNotFoundError,
    ShiftNotFoundError,
    ShiftService,
    ShiftServiceError,
    UpdateShiftCommand,
)

router = APIRouter(prefix="/shifts", tags=["shifts"])


@lru_cache
def get_shift_repository() -> PostgresShiftRepository:
    return PostgresShiftRepository()


def get_shift_service(
    repository: Annotated[ShiftRepository, Depends(get_shift_repository)],
) -> ShiftService:
    return ShiftService(repository)


@router.get("", response_model=list[ShiftResponse])
def list_shifts(
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ShiftService, Depends(get_shift_service)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[ShiftResponse]:
    try:
        records = service.list_shifts(connection, date_from, date_to)
    except ShiftServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return [ShiftResponse.model_validate(record) for record in records]


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreateRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ShiftService, Depends(get_shift_service)],
) -> ShiftResponse:
    try:
        record = service.create_shift(
            connection,
            CreateShiftCommand(
                start_at=payload.start_at,
                end_at=payload.end_at,
                break_minutes=payload.break_minutes,
                shift_type=payload.shift_type,
                notes=payload.notes,
            ),
        )
    except ProfileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ShiftServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ShiftResponse.model_validate(record)


@router.patch("/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: UUID,
    payload: ShiftUpdateRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ShiftService, Depends(get_shift_service)],
) -> ShiftResponse:
    try:
        record = service.update_shift(
            connection,
            shift_id,
            UpdateShiftCommand(
                start_at=payload.start_at,
                end_at=payload.end_at,
                break_minutes=payload.break_minutes,
                shift_type=payload.shift_type,
                notes=payload.notes,
                notes_supplied="notes" in payload.model_fields_set,
            ),
        )
    except (ProfileNotFoundError, ShiftNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ShiftServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ShiftResponse.model_validate(record)


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(
    shift_id: UUID,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ShiftService, Depends(get_shift_service)],
) -> Response:
    try:
        service.delete_shift(connection, shift_id)
    except ShiftNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
