from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import Connection, Engine
from starlette.concurrency import run_in_threadpool

from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.database import (
    authenticated_connection,
    get_database_engine,
    user_connection,
)
from backend.app.core.quotas import (
    RequestQuotaGuard,
    consume_upload_quota,
    get_request_quota_guard,
    quota_callback,
)
from backend.app.core.settings import Settings, get_settings
from backend.app.integrations.gemini import GeminiScheduleExtractor, ScheduleExtractor
from backend.app.repositories.imports import ImportRepository, PostgresImportRepository
from backend.app.schemas.imports import (
    ImportCommitResponse,
    ImportItemUpdateRequest,
    ShiftImportResponse,
)
from backend.app.services.imports import (
    ImportConflictError,
    ImportNotFoundError,
    ImportService,
    ImportServiceError,
    ValidatedUploadInfo,
)
from backend.app.services.upload_validation import (
    UploadValidationError,
    cleanup_temporary_upload,
    validate_to_temporary_file,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@lru_cache
def get_import_repository() -> PostgresImportRepository:
    return PostgresImportRepository()


def get_schedule_extractor(
    settings: Annotated[Settings, Depends(get_settings)],
    quota_guard: Annotated[RequestQuotaGuard, Depends(get_request_quota_guard)],
) -> ScheduleExtractor:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_NOT_CONFIGURED")
    return GeminiScheduleExtractor(
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_timeout_seconds,
        quota_callback(quota_guard),
    )


def get_import_service(
    repository: Annotated[ImportRepository, Depends(get_import_repository)],
) -> ImportService:
    return ImportService(repository)


@router.post(
    "", response_model=ShiftImportResponse, status_code=status.HTTP_201_CREATED
)
async def create_import(
    file: Annotated[UploadFile, File()],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    engine: Annotated[Engine, Depends(get_database_engine)],
    service: Annotated[ImportService, Depends(get_import_service)],
    extractor: Annotated[ScheduleExtractor, Depends(get_schedule_extractor)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(consume_upload_quota)],
) -> ShiftImportResponse:
    try:
        upload = await validate_to_temporary_file(
            file, settings.upload_max_bytes, settings.upload_pdf_max_pages
        )
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        upload_info = ValidatedUploadInfo(
            path=upload.path,
            filename=upload.filename,
            media_type=upload.media_type,
            sha256=upload.sha256,
        )
        extraction_service = ImportService(service.repository, extractor)
        with authenticated_connection(engine, user) as connection:
            import_id, timezone = extraction_service.create_draft(
                connection, upload_info
            )
        items, error_code = await run_in_threadpool(
            extraction_service.extract, upload_info, timezone
        )
        with authenticated_connection(engine, user) as connection:
            record = extraction_service.complete_extraction(
                connection, import_id, items, error_code
            )
    finally:
        cleanup_temporary_upload(upload)
    return ShiftImportResponse.model_validate(record)


@router.get("/{import_id}", response_model=ShiftImportResponse)
def get_import(
    import_id: UUID,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ShiftImportResponse:
    try:
        return ShiftImportResponse.model_validate(
            service.get_import(connection, import_id)
        )
    except ImportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/{import_id}/items/{item_id}", response_model=ShiftImportResponse)
def update_import_item(
    import_id: UUID,
    item_id: UUID,
    payload: ImportItemUpdateRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ShiftImportResponse:
    try:
        return ShiftImportResponse.model_validate(
            service.update_item(connection, import_id, item_id, payload)
        )
    except ImportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ImportConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ImportServiceError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{import_id}/commit", response_model=ImportCommitResponse)
def commit_import(
    import_id: UUID,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportCommitResponse:
    try:
        ids = service.commit(connection, import_id)
    except ImportNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ImportConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ImportCommitResponse(
        import_id=import_id, status="committed", created_shift_ids=ids
    )
