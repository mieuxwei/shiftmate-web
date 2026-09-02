from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection

from backend.app.api.v1.analytics import get_analytics_service
from backend.app.api.v1.policies import get_policy_service
from backend.app.core.database import user_connection
from backend.app.core.quotas import (
    RequestQuotaGuard,
    get_request_quota_guard,
    quota_callback,
)
from backend.app.core.settings import Settings, get_settings
from backend.app.integrations.gemini_assistant import GeminiAssistantAdapter
from backend.app.integrations.gemini_rag import GeminiEmbeddings, GeminiRagError
from backend.app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from backend.app.services.analytics import (
    AnalyticsCalculationError,
    AnalyticsService,
    AnalyticsServiceError,
)
from backend.app.services.assistant_factory import build_assistant_service
from backend.app.services.policies import PolicyService
from backend.app.services.shifts import ProfileNotFoundError

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_model(
    settings: Annotated[Settings, Depends(get_settings)],
    quota_guard: Annotated[RequestQuotaGuard, Depends(get_request_quota_guard)],
) -> GeminiAssistantAdapter | None:
    if not settings.gemini_api_key:
        return None
    return GeminiAssistantAdapter(
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_timeout_seconds,
        quota_callback(quota_guard),
    )


def get_assistant_embeddings(
    settings: Annotated[Settings, Depends(get_settings)],
    quota_guard: Annotated[RequestQuotaGuard, Depends(get_request_quota_guard)],
) -> Embeddings | None:
    if not settings.gemini_api_key:
        return None
    return GeminiEmbeddings(
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        settings.gemini_timeout_seconds,
        settings.gemini_embedding_dimensions,
        quota_callback(quota_guard),
    )


@router.post("/query", response_model=AssistantQueryResponse)
def query_assistant(
    payload: AssistantQueryRequest,
    connection: Annotated[Connection, Depends(user_connection)],
    analytics: Annotated[AnalyticsService, Depends(get_analytics_service)],
    policies: Annotated[PolicyService, Depends(get_policy_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    model: Annotated[GeminiAssistantAdapter | None, Depends(get_assistant_model)],
    embeddings: Annotated[Embeddings | None, Depends(get_assistant_embeddings)],
) -> AssistantQueryResponse:
    service = build_assistant_service(
        analytics,
        policies,
        embeddings,
        model,
        top_k=settings.rag_top_k,
        score_threshold=settings.rag_score_threshold,
    )
    try:
        return service.query(
            connection,
            payload.question,
            payload.date_from,
            payload.date_to,
        )
    except GeminiRagError as error:
        raise HTTPException(status_code=503, detail=error.code) from error
    except ProfileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (AnalyticsServiceError, AnalyticsCalculationError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
