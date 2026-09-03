import httpx
import pytest

from backend.app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def api_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_endpoint() -> None:
    async with api_client() as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


async def test_openapi_contains_health_endpoint() -> None:
    async with api_client() as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["version"] == "1.0.0"
    assert "/api/v1/health" in schema["paths"]


async def test_unknown_api_route_does_not_fall_back_to_frontend() -> None:
    async with api_client() as client:
        response = await client.get("/api/v1/missing")

    assert response.status_code == 404
