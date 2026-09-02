from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.v1.router import api_router
from backend.app.core.settings import get_settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="ShiftMate Web API",
        version="0.1.0",
        description="API for the ShiftMate Web portfolio application.",
    )
    app.include_router(api_router)

    frontend_dist = get_settings().frontend_dist_dir.resolve()
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
