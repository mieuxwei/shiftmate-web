from datetime import date

from pydantic import BaseModel


class MaintenanceResponse(BaseModel):
    status: str
    logical_run_date: date
    expired_drafts: int
    deleted_drafts: int
    stale_statuses: int
    deleted_usage_rows: int
    deleted_audit_rows: int
