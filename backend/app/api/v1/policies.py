from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection, Engine
from starlette.concurrency import run_in_threadpool

from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.database import (
    authenticated_connection,
    get_database_engine,
    user_connection,
)
from backend.app.core.settings import Settings, get_settings
from backend.app.integrations.gemini_rag import (
    GeminiEmbeddings,
    GeminiGroundedAnswerer,
    GeminiRagError,
)
from backend.app.repositories.policies import (
    PolicyRepository,
    PostgresPolicyRepository,
)
from backend.app.schemas.policies import (
    PolicyAnswerResponse,
    PolicyDocumentResponse,
    PolicyQueryRequest,
    PolicyUploadResponse,
)
from backend.app.services.policies import (
    GroundedAnswerer,
    PolicyNotFoundError,
    PolicyService,
    PolicyServiceError,
    PolicyUploadInfo,
)
from backend.app.services.policy_text import PolicyTextError
from backend.app.services.upload_validation import (
    UploadValidationError,
    cleanup_temporary_upload,
    validate_to_temporary_file,
)

router = APIRouter(prefix="/policies", tags=["policies"])
assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])


@lru_cache
def get_policy_repository() -> PostgresPolicyRepository:
    return PostgresPolicyRepository()


def get_policy_service(
    repository: Annotated[PolicyRepository, Depends(get_policy_repository)],
) -> PolicyService:
    return PolicyService(repository)


def get_policy_embeddings(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Embeddings:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_NOT_CONFIGURED")
    return GeminiEmbeddings(
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        settings.gemini_timeout_seconds,
        settings.gemini_embedding_dimensions,
    )


def get_grounded_answerer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GroundedAnswerer:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_NOT_CONFIGURED")
    return GeminiGroundedAnswerer(
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_timeout_seconds,
    )


@router.post(
    "", response_model=PolicyUploadResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    response: Response,
    title: Annotated[str, Form(min_length=1, max_length=200)],
    confirm_safe_data: Annotated[bool, Form()],
    file: Annotated[UploadFile, File()],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    engine: Annotated[Engine, Depends(get_database_engine)],
    service: Annotated[PolicyService, Depends(get_policy_service)],
    embeddings: Annotated[Embeddings, Depends(get_policy_embeddings)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PolicyUploadResponse:
    if not confirm_safe_data:
        raise HTTPException(
            status_code=422, detail="POLICY_SAFE_DATA_CONFIRMATION_REQUIRED"
        )
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="POLICY_TITLE_REQUIRED")
    try:
        upload = await validate_to_temporary_file(
            file, settings.upload_max_bytes, settings.upload_pdf_max_pages
        )
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        if upload.media_type != "application/pdf" or upload.page_count is None:
            raise HTTPException(status_code=422, detail="POLICY_PDF_REQUIRED")
        upload_info = PolicyUploadInfo(
            path=upload.path,
            title=title,
            filename=upload.filename,
            sha256=upload.sha256,
            page_count=upload.page_count,
        )
        with authenticated_connection(engine, user) as connection:
            document, duplicate = service.create_draft(connection, upload_info)
        if duplicate:
            response.status_code = status.HTTP_200_OK
            return PolicyUploadResponse(
                document=PolicyDocumentResponse.model_validate(document),
                duplicate=True,
            )
        try:
            chunks = await run_in_threadpool(
                service.prepare_chunks, upload_info, embeddings
            )
        except (GeminiRagError, PolicyTextError, PolicyServiceError) as error:
            code = (
                error.code
                if isinstance(error, (GeminiRagError, PolicyTextError))
                else str(error)
            )
            with authenticated_connection(engine, user) as connection:
                failed = service.fail_indexing(connection, document.id, code)
            return PolicyUploadResponse(
                document=PolicyDocumentResponse.model_validate(failed),
                duplicate=False,
            )
        with authenticated_connection(engine, user) as connection:
            ready = service.complete_indexing(connection, document.id, chunks)
        return PolicyUploadResponse(
            document=PolicyDocumentResponse.model_validate(ready),
            duplicate=False,
        )
    finally:
        cleanup_temporary_upload(upload)


@router.get("", response_model=list[PolicyDocumentResponse])
def list_policies(
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PolicyService, Depends(get_policy_service)],
) -> list[PolicyDocumentResponse]:
    return [
        PolicyDocumentResponse.model_validate(document)
        for document in service.list_documents(connection)
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    document_id: UUID,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PolicyService, Depends(get_policy_service)],
) -> Response:
    try:
        service.delete_document(connection, document_id)
    except PolicyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@assistant_router.post("/query", response_model=PolicyAnswerResponse)
def query_policy(
    payload: PolicyQueryRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    service: Annotated[PolicyService, Depends(get_policy_service)],
    embeddings: Annotated[Embeddings, Depends(get_policy_embeddings)],
    answerer: Annotated[GroundedAnswerer, Depends(get_grounded_answerer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PolicyAnswerResponse:
    try:
        return service.answer_question(
            connection,
            payload.question,
            embeddings,
            answerer,
            settings.rag_top_k,
            settings.rag_score_threshold,
        )
    except GeminiRagError as error:
        raise HTTPException(status_code=503, detail=error.code) from error
