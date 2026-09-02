import os
from collections.abc import Iterator
from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.app.services.maintenance import MaintenanceService

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = os.environ.get("M2_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M2_TEST_DATABASE_URL is not set")
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(Config("alembic.ini"), "head")
        yield url
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def test_durable_owner_and_app_daily_caps(database_url: str) -> None:
    engine = create_engine(database_url, connect_args={"prepare_threshold": None})
    owner_id = uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO profiles (id, display_name) "
                    "VALUES (:id, 'Synthetic Quota User')"
                ),
                {"id": owner_id},
            )
            connection.execute(
                text("SELECT set_config('request.jwt.claim.sub', :id, true)"),
                {"id": str(owner_id)},
            )
            assert connection.execute(
                text("SELECT app_private.consume_owner_daily_quota('upload', 2)")
            ).scalar_one()
            assert connection.execute(
                text("SELECT app_private.consume_owner_daily_quota('upload', 2)")
            ).scalar_one()
            assert not connection.execute(
                text("SELECT app_private.consume_owner_daily_quota('upload', 2)")
            ).scalar_one()
            assert connection.execute(
                text("SELECT app_private.consume_app_daily_quota('gemini_request', 1)")
            ).scalar_one()
            assert not connection.execute(
                text("SELECT app_private.consume_app_daily_quota('gemini_request', 1)")
            ).scalar_one()
    finally:
        engine.dispose()


def test_duplicate_maintenance_run_has_no_second_side_effect(
    database_url: str,
) -> None:
    engine = create_engine(database_url, connect_args={"prepare_threshold": None})
    owner_id = uuid4()
    import_id = uuid4()
    logical_date = date(2026, 9, 3)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO profiles (id, display_name) "
                    "VALUES (:id, 'Synthetic Maintenance User')"
                ),
                {"id": owner_id},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO shift_imports (
                        id, owner_id, filename, media_type, sha256, status, created_at
                    ) VALUES (
                        :id, :owner_id, 'synthetic.png', 'image/png', :sha,
                        'review', now() - interval '8 days'
                    )
                    """
                ),
                {"id": import_id, "owner_id": owner_id, "sha": "f" * 64},
            )
            connection.execute(
                text(
                    "DELETE FROM scheduled_job_runs "
                    "WHERE job_name = 'daily-maintenance' "
                    "AND logical_run_date = :logical_date"
                ),
                {"logical_date": logical_date},
            )

        service = MaintenanceService(engine)
        first = service.run(logical_date, draft_ttl_days=7, retention_days=30)
        second = service.run(logical_date, draft_ttl_days=7, retention_days=30)

        assert first.status == "succeeded"
        assert first.expired_drafts == 1
        assert second.status == "skipped"
        assert second.expired_drafts == 0
        with engine.connect() as connection:
            status = connection.execute(
                text("SELECT status FROM shift_imports WHERE id = :id"),
                {"id": import_id},
            ).scalar_one()
        assert status == "expired"
    finally:
        engine.dispose()
