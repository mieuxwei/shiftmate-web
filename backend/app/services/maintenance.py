from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, Engine, text

from backend.app.core.database import maintenance_connection

JOB_NAME = "daily-maintenance"


@dataclass(frozen=True, slots=True)
class MaintenanceResult:
    status: str
    logical_run_date: date
    expired_drafts: int = 0
    deleted_drafts: int = 0
    stale_statuses: int = 0
    deleted_usage_rows: int = 0
    deleted_audit_rows: int = 0


class MaintenanceService:
    def __init__(self, engine: Engine, role: str = "shiftmate_maintenance") -> None:
        self.engine = engine
        self.role = role

    def run(
        self, logical_run_date: date, draft_ttl_days: int, retention_days: int
    ) -> MaintenanceResult:
        key = f"{JOB_NAME}:{logical_run_date.isoformat()}"
        with maintenance_connection(self.engine, self.role) as connection:
            claimed = connection.execute(
                text(
                    """
                    INSERT INTO scheduled_job_runs (
                        job_name, logical_run_date, status, idempotency_key, started_at
                    ) VALUES (
                        :job_name, :logical_run_date, 'running', :key, now()
                    ) ON CONFLICT (job_name, logical_run_date) DO UPDATE
                    SET status = 'running', started_at = now(), finished_at = NULL,
                        last_error_code = NULL
                    WHERE scheduled_job_runs.status = 'failed'
                       OR (
                            scheduled_job_runs.status = 'running'
                            AND scheduled_job_runs.started_at
                                < now() - interval '1 hour'
                       )
                    RETURNING id
                    """
                ),
                {
                    "job_name": JOB_NAME,
                    "logical_run_date": logical_run_date,
                    "key": key,
                },
            ).scalar_one_or_none()
        if claimed is None:
            return MaintenanceResult("skipped", logical_run_date)

        try:
            with maintenance_connection(self.engine, self.role) as connection:
                result = self._perform(
                    connection, logical_run_date, draft_ttl_days, retention_days
                )
                connection.execute(
                    text(
                        """
                        UPDATE scheduled_job_runs
                        SET status = 'succeeded', finished_at = now(),
                            last_error_code = NULL
                        WHERE id = :run_id
                        """
                    ),
                    {"run_id": claimed},
                )
            return result
        except Exception:
            with maintenance_connection(self.engine, self.role) as connection:
                connection.execute(
                    text(
                        """
                        UPDATE scheduled_job_runs
                        SET status = 'failed', finished_at = now(),
                            last_error_code = 'MAINTENANCE_FAILED'
                        WHERE id = :run_id
                        """
                    ),
                    {"run_id": claimed},
                )
            raise

    @staticmethod
    def _perform(
        connection: Connection,
        logical_run_date: date,
        draft_ttl_days: int,
        retention_days: int,
    ) -> MaintenanceResult:
        expired = connection.execute(
            text(
                """
                UPDATE shift_imports SET status = 'expired', updated_at = now()
                WHERE status IN ('uploaded', 'extracting', 'review', 'failed')
                  AND created_at < now() - make_interval(days => :ttl)
                """
            ),
            {"ttl": draft_ttl_days},
        ).rowcount
        deleted = connection.execute(
            text(
                """
                DELETE FROM shift_imports
                WHERE status = 'expired'
                  AND created_at < now() - make_interval(days => :retention)
                """
            ),
            {"retention": retention_days},
        ).rowcount
        stale_policies = connection.execute(
            text(
                """
                UPDATE policy_documents
                SET status = 'failed', error_code = 'STALE_INDEXING', updated_at = now()
                WHERE status = 'indexing' AND updated_at < now() - interval '1 day'
                """
            )
        ).rowcount
        stale_calendar = connection.execute(
            text(
                """
                UPDATE calendar_sync_records
                SET status = 'failed', last_error_code = 'STALE_PENDING',
                    updated_at = now()
                WHERE status = 'pending' AND updated_at < now() - interval '1 day'
                """
            )
        ).rowcount
        usage_rows = 0
        for table_name in ("owner_daily_quotas", "app_daily_quotas"):
            usage_rows += connection.execute(
                text(
                    f"DELETE FROM {table_name} WHERE usage_date < :logical_run_date - 2"
                ),
                {"logical_run_date": logical_run_date},
            ).rowcount
        audit_rows = connection.execute(
            text(
                """
                DELETE FROM tool_audit_logs
                WHERE created_at < now() - make_interval(days => :retention)
                """
            ),
            {"retention": retention_days},
        ).rowcount
        return MaintenanceResult(
            "succeeded",
            logical_run_date,
            expired,
            deleted,
            stale_policies + stale_calendar,
            usage_rows,
            audit_rows,
        )
