import json
import logging
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from jwt import PyJWK
from jwt.algorithms import RSAAlgorithm

from backend.app.core.http_security import FixedWindowRateLimiter
from backend.app.core.internal_auth import (
    InvalidSchedulerToken,
    SchedulerOidcVerifier,
)
from backend.app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StaticKeys:
    def __init__(self, key: PyJWK) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        del token
        return self.key


def scheduler_token(
    *, email: str = "scheduler@synthetic-project.iam.gserviceaccount.com"
) -> tuple[str, SchedulerOidcVerifier]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "synthetic-scheduler-key", "alg": "RS256", "use": "sig"})
    audience = "https://shiftmate-synthetic.run.app"
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "aud": audience,
            "email": email,
            "email_verified": True,
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "iss": "https://accounts.google.com",
            "sub": str(uuid4()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "synthetic-scheduler-key"},
    )
    verifier = SchedulerOidcVerifier(audience, email, StaticKeys(PyJWK.from_dict(jwk)))
    return token, verifier


def test_rate_limiter_rejects_burst_and_recovers_after_window() -> None:
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("synthetic-peer", now=0) == (True, 0)
    assert limiter.allow("synthetic-peer", now=1) == (True, 0)
    allowed, retry_after = limiter.allow("synthetic-peer", now=2)
    assert allowed is False
    assert retry_after == 58
    assert limiter.allow("synthetic-peer", now=61) == (True, 0)


def test_scheduler_oidc_requires_exact_audience_email_and_verified_claim() -> None:
    token, verifier = scheduler_token()

    assert verifier.verify(token).email == (
        "scheduler@synthetic-project.iam.gserviceaccount.com"
    )

    wrong_token, _ = scheduler_token(email="other@synthetic.invalid")
    with pytest.raises(InvalidSchedulerToken):
        verifier.verify(wrong_token)


async def test_internal_endpoint_rejects_request_without_oidc() -> None:
    transport = httpx.ASGITransport(app=cast(FastAPI, app))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/daily-maintenance",
            headers={
                "X-CloudScheduler-JobName": "daily-maintenance",
                "X-CloudScheduler-ScheduleTime": "2026-09-03T03:15:00+08:00",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "SCHEDULER_UNAUTHORIZED"}


async def test_structured_http_log_omits_headers_query_and_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="shiftmate.http")
    transport = httpx.ASGITransport(app=cast(FastAPI, app))
    secret = "synthetic-private-marker"
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/policies/00000000-0000-4000-8000-000000000009?private={secret}",
            headers={"Authorization": f"Bearer {secret}"},
        )

    assert response.status_code in {401, 404, 503}
    messages = [
        record.message for record in caplog.records if record.name == "shiftmate.http"
    ]
    assert messages, "Expected a structured shiftmate.http request log"
    log = messages[-1]
    assert secret not in log
    assert json.loads(log)["path"] == "/api/v1/policies/{id}"
