from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1.router import api_router
from backend.app.core.settings import get_settings
from backend.app.mcp.server import build_http_mcp_app


def create_app() -> FastAPI:
    settings = get_settings()
    mcp_http_app = build_http_mcp_app(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with mcp_http_app.router.lifespan_context(mcp_http_app):
            yield

    app = FastAPI(
        title="ShiftMate Web API",
        version="0.1.0",
        description="API for the ShiftMate Web portfolio application.",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    app.mount("/mcp", mcp_http_app, name="mcp")

    frontend_dist = settings.frontend_dist_dir.resolve()
    assets_dir = frontend_dist / "assets"

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        requested_file = (frontend_dist / path).resolve()
        if (
            path
            and requested_file.is_relative_to(frontend_dist)
            and requested_file.is_file()
        ):
            return FileResponse(requested_file)

        index_file = frontend_dist / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        raise HTTPException(
            status_code=503,
            detail="Frontend build unavailable; use the Vite development server.",
        )

    return app


app = create_app()
