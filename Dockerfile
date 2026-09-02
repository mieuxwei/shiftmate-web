# syntax=docker/dockerfile:1

FROM node:24-alpine AS frontend-build
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    FRONTEND_DIST_DIR=/app/frontend/dist
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
USER app
EXPOSE 8080
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM runtime AS test
USER root
RUN pip install --no-cache-dir ".[dev]"
COPY evals/ ./evals/
COPY frontend/src/demo/ ./frontend/src/demo/
ENV APP_ENV=development
USER app
CMD ["pytest", "-o", "cache_dir=/tmp/.pytest_cache", "--cov=backend.app", "--cov-report=term-missing"]
