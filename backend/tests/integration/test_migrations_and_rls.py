import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, text

from backend.app.core.auth import AuthenticatedUser
from backend.app.core.database import user_connection
from backend.app.repositories.shifts import PostgresShiftRepository

pytestmark = pytest.mark.integration

OWNER_TABLES = {
    "profiles",
    "shifts",
    "pay_rates",
    "shift_imports",
    "shift_import_items",
    "policy_documents",
    "policy_chunks",
    "calendar_connections",
    "calendar_sync_records",
    "chat_sessions",
    "chat_messages",
    "tool_audit_logs",
    "owner_daily_quotas",
}
APPLICATION_TABLES = OWNER_TABLES | {"scheduled_job_runs", "app_daily_quotas"}


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = os.environ.get("M2_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M2_TEST_DATABASE_URL is not set")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        yield url
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def migrate(revision: str) -> None:
    command.upgrade(Config("alembic.ini"), revision)


def downgrade(revision: str) -> None:
    command.downgrade(Config("alembic.ini"), revision)


@contextmanager
def request_connection(
    database_url: str, role_name: str, user_id: UUID
) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(psycopg_url(database_url)) as connection:
        connection.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
        connection.execute(
            "SELECT set_config('request.jwt.claim.sub', %s, true)", (str(user_id),)
        )
        yield connection


def test_migration_round_trip_builds_expected_schema(database_url: str) -> None:
    downgrade("base")
    migrate("head")

    with psycopg.connect(psycopg_url(database_url)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            ).fetchall()
        }
        index_definition = connection.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = 'ix_shifts_owner_work_date'
            """
        ).fetchone()
        rls_flags = {
            row[0]: (row[1], row[2])
            for row in connection.execute(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = ANY(%s)
                """,
                (list(APPLICATION_TABLES),),
            ).fetchall()
        }
        owner_policies = {
            row[0]: (row[1], row[2])
            for row in connection.execute(
                """
                SELECT tablename, qual, with_check
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = ANY(%s)
                  AND policyname LIKE '%%owner_isolation'
                """,
                (list(OWNER_TABLES),),
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                """
            ).fetchall()
        }
        extension_names = {
            row[0]
            for row in connection.execute(
                "SELECT extname FROM pg_extension "
                "WHERE extname IN ('pgcrypto', 'vector')"
            ).fetchall()
        }
        vector_distance = connection.execute(
            "SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector"
        ).fetchone()
        job_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'scheduled_job_runs'::regclass
                """
            ).fetchall()
        }
        shift_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'shifts'::regclass
                """
            ).fetchall()
        }
        chat_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'chat_messages'
                """
            ).fetchall()
        }
        import_item_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'shift_import_items'::regclass
                """
            ).fetchall()
        }
        policy_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'policy_documents'::regclass
                """
            ).fetchall()
        }
        calendar_connection_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'calendar_connections'::regclass
                """
            ).fetchall()
        }
        calendar_sync_constraints = {
            row[0]
            for row in connection.execute(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'calendar_sync_records'::regclass
                """
            ).fetchall()
        }
        embedding_type = connection.execute(
            """
            SELECT format_type(attribute.atttypid, attribute.atttypmod)
            FROM pg_attribute AS attribute
            WHERE attribute.attrelid = 'policy_chunks'::regclass
              AND attribute.attname = 'embedding'
            """
        ).fetchone()

    assert APPLICATION_TABLES | {"alembic_version"} <= tables
    assert index_definition is not None
    assert "(owner_id, work_date)" in index_definition[0]
    assert rls_flags == {table: (True, True) for table in APPLICATION_TABLES}
    assert owner_policies.keys() == OWNER_TABLES
    for using_expression, check_expression in owner_policies.values():
        assert "current_user_id()" in using_expression
        assert "current_user_id()" in check_expression
    assert "scheduled_job_runs" not in owner_policies
    assert "app_daily_quotas" not in owner_policies
    assert extension_names == {"pgcrypto", "vector"}
    assert vector_distance == (1.0,)
    assert {
        "ix_pay_rates_owner_effective_from",
        "ix_policy_chunks_owner_document",
        "ix_policy_chunks_embedding_cosine",
        "ix_shift_import_items_import",
        "ix_shift_imports_owner_created_at",
    } <= indexes
    assert {
        "ck_shifts_break_minutes",
        "ck_shifts_end_after_start",
        "ck_shifts_source",
        "shifts_owner_id_fkey",
        "shifts_pkey",
        "uq_shifts_id_owner",
    } <= shift_constraints
    assert {
        "uq_scheduled_job_runs_idempotency_key",
        "uq_scheduled_job_runs_job_date",
    } <= job_constraints
    assert "chain_of_thought" not in chat_columns
    assert {
        "fk_shift_import_items_committed_shift",
        "uq_shift_import_items_import_index",
        "uq_shift_import_items_committed_shift",
    } <= import_item_constraints
    assert "uq_policy_documents_owner_sha256" in policy_constraints
    assert "uq_calendar_connections_owner" in calendar_connection_constraints
    assert {
        "uq_calendar_sync_records_owner_shift",
        "fk_calendar_sync_records_shift_owner",
    } <= calendar_sync_constraints
    assert embedding_type == ("vector(768)",)

    downgrade("base")
    with psycopg.connect(psycopg_url(database_url)) as connection:
        remaining = connection.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename = ANY(%s)
            """,
            (list(APPLICATION_TABLES),),
        ).fetchall()
    assert remaining == []

    migrate("head")


def test_rls_prevents_cross_owner_reads_and_writes(database_url: str) -> None:
    downgrade("base")
    migrate("head")

    user_a = uuid4()
    user_b = uuid4()
    shift_a = uuid4()
    shift_b = uuid4()
    import_a = uuid4()
    policy_a = uuid4()
    policy_b = uuid4()
    chunk_a = uuid4()
    chunk_b = uuid4()
    role_name = f"shiftmate_test_{uuid4().hex}"
    start_at = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)

    with psycopg.connect(psycopg_url(database_url), autocommit=True) as admin:
        admin.execute(
            """
            INSERT INTO profiles (id, display_name)
            VALUES (%s, 'Synthetic User A'), (%s, 'Synthetic User B')
            """,
            (user_a, user_b),
        )
        admin.execute(
            """
            INSERT INTO pay_rates (owner_id, hourly_rate, effective_from)
            VALUES (%s, 200, '2026-09-01'), (%s, 300, '2026-09-01')
            """,
            (user_a, user_b),
        )
        admin.execute(
            """
            INSERT INTO shift_imports (
                id, owner_id, filename, media_type, sha256
            )
            VALUES (%s, %s, 'synthetic.png', 'image/png', %s)
            """,
            (import_a, user_a, "a" * 64),
        )
        embedding = "[1," + ",".join("0" for _ in range(767)) + "]"
        admin.execute(
            """
            INSERT INTO policy_documents (
                id, owner_id, title, filename, sha256, status, page_count
            ) VALUES
                (%s, %s, 'Synthetic Policy A', 'a.pdf', %s, 'ready', 1),
                (%s, %s, 'Synthetic Policy B', 'b.pdf', %s, 'ready', 1)
            """,
            (policy_a, user_a, "b" * 64, policy_b, user_b, "c" * 64),
        )
        admin.execute(
            """
            INSERT INTO policy_chunks (
                id, document_id, owner_id, content, page_number, chunk_index,
                embedding
            ) VALUES
                (%s, %s, %s, 'Owner A policy text', 1, 0, %s::vector),
                (%s, %s, %s, 'Owner B secret policy text', 1, 0, %s::vector)
            """,
            (
                chunk_a,
                policy_a,
                user_a,
                embedding,
                chunk_b,
                policy_b,
                user_b,
                embedding,
            ),
        )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            admin.execute(
                """
                INSERT INTO shift_import_items (import_id, owner_id, item_index)
                VALUES (%s, %s, 0)
                """,
                (import_a, user_b),
            )
        admin.execute(
            """
            INSERT INTO shifts (
                id, owner_id, work_date, start_at, end_at, shift_type
            )
            VALUES
                (%s, %s, %s, %s, %s, 'day'),
                (%s, %s, %s, %s, %s, 'day')
            """,
            (
                shift_a,
                user_a,
                date(2026, 9, 2),
                start_at,
                start_at + timedelta(hours=8),
                shift_b,
                user_b,
                date(2026, 9, 3),
                start_at,
                start_at + timedelta(hours=8),
            ),
        )
        admin.execute(
            sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role_name))
        )
        admin.execute(
            sql.SQL("GRANT {} TO CURRENT_USER").format(sql.Identifier(role_name))
        )
        admin.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public, app_private TO {}").format(
                sql.Identifier(role_name)
            )
        )
        admin.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                "IN SCHEMA public TO {}"
            ).format(sql.Identifier(role_name))
        )

    try:
        with request_connection(database_url, role_name, user_a) as connection:
            visible_profiles = connection.execute(
                "SELECT id FROM profiles ORDER BY id"
            ).fetchall()
            visible_shifts = connection.execute(
                "SELECT id FROM shifts ORDER BY id"
            ).fetchall()
            visible_pay_rates = connection.execute(
                "SELECT owner_id FROM pay_rates ORDER BY owner_id"
            ).fetchall()
            visible_job_runs = connection.execute(
                "SELECT id FROM scheduled_job_runs"
            ).fetchall()
            visible_policy_chunks = connection.execute(
                """
                SELECT id, content FROM policy_chunks
                ORDER BY embedding <=> %s::vector
                """,
                (embedding,),
            ).fetchall()
            cross_owner_update = connection.execute(
                "UPDATE shifts SET notes = 'blocked' WHERE id = %s", (shift_b,)
            )
            cross_owner_delete = connection.execute(
                "DELETE FROM shifts WHERE id = %s", (shift_b,)
            )

        assert visible_profiles == [(user_a,)]
        assert visible_shifts == [(shift_a,)]
        assert visible_pay_rates == [(user_a,)]
        assert visible_job_runs == []
        assert visible_policy_chunks == [(chunk_a, "Owner A policy text")]
        assert cross_owner_update.rowcount == 0
        assert cross_owner_delete.rowcount == 0

        engine = create_engine(database_url, connect_args={"prepare_threshold": None})
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(f'SET LOCAL ROLE "{role_name}"')
                connection.execute(
                    text("SELECT set_config('request.jwt.claim.sub', :user_id, true)"),
                    {"user_id": str(user_a)},
                )
                repository_ids = PostgresShiftRepository().list_ids(connection)
            assert repository_ids == [shift_a]
        finally:
            engine.dispose()

        with (
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            request_connection(database_url, role_name, user_a) as connection,
        ):
            connection.execute(
                """
                INSERT INTO shifts (
                    owner_id, work_date, start_at, end_at, shift_type
                )
                VALUES (%s, %s, %s, %s, 'day')
                """,
                (
                    user_b,
                    date(2026, 9, 4),
                    start_at,
                    start_at + timedelta(hours=8),
                ),
            )

        with request_connection(database_url, role_name, user_a) as connection:
            inserted = connection.execute(
                """
                INSERT INTO shifts (
                    owner_id, work_date, start_at, end_at, shift_type
                )
                VALUES (%s, %s, %s, %s, 'day')
                RETURNING owner_id
                """,
                (
                    user_a,
                    date(2026, 9, 4),
                    start_at,
                    start_at + timedelta(hours=8),
                ),
            ).fetchone()
        assert inserted == (user_a,)
    finally:
        with psycopg.connect(psycopg_url(database_url), autocommit=True) as admin:
            admin.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role_name)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role_name)))


def test_request_connection_sets_and_clears_transaction_identity(
    database_url: str,
) -> None:
    downgrade("base")
    migrate("head")
    user_id = uuid4()
    shift_id = uuid4()
    engine = create_engine(database_url, connect_args={"prepare_threshold": None})

    with psycopg.connect(psycopg_url(database_url), autocommit=True) as admin:
        admin.execute("CREATE ROLE authenticated NOLOGIN NOBYPASSRLS")
        admin.execute("GRANT authenticated TO CURRENT_USER")
        admin.execute("GRANT USAGE ON SCHEMA public, app_private TO authenticated")
        admin.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON profiles, shifts TO authenticated"
        )
        admin.execute(
            "INSERT INTO profiles (id, display_name) VALUES (%s, 'Synthetic User')",
            (user_id,),
        )
        admin.execute(
            """
            INSERT INTO shifts (
                id, owner_id, work_date, start_at, end_at, shift_type
            )
            VALUES (%s, %s, '2026-09-05', %s, %s, 'day')
            """,
            (
                shift_id,
                user_id,
                datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
                datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
            ),
        )

    dependency = user_connection(
        AuthenticatedUser(id=user_id, role="authenticated"), engine
    )
    try:
        connection = next(dependency)
        identity = connection.execute(
            text(
                """
                SELECT current_user,
                       current_setting('request.jwt.claim.sub', true)
                """
            )
        ).one()
        assert identity == ("authenticated", str(user_id))
        assert PostgresShiftRepository().list_ids(connection) == [shift_id]
    finally:
        dependency.close()

    try:
        with engine.connect() as connection:
            cleared = connection.execute(
                text(
                    """
                    SELECT current_user,
                           current_setting('request.jwt.claim.sub', true)
                    """
                )
            ).one()
        assert cleared == ("postgres", "")
    finally:
        engine.dispose()
        with psycopg.connect(psycopg_url(database_url), autocommit=True) as admin:
            admin.execute("DROP OWNED BY authenticated")
            admin.execute("DROP ROLE authenticated")
