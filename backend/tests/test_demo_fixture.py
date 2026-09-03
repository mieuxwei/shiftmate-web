import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.app.domain.analytics import calculate_schedule_summary
from backend.app.domain.schedule import PayRate, Shift

FIXTURE_PATH = Path("frontend/src/demo/schedule-demo.json")


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


def test_synthetic_demo_summary_matches_domain_calculation() -> None:
    fixture = load_fixture()
    profile = fixture["profile"]
    shifts = [
        Shift(
            start_at=datetime.fromisoformat(item["start_at"].replace("Z", "+00:00")),
            end_at=datetime.fromisoformat(item["end_at"].replace("Z", "+00:00")),
            break_minutes=item["break_minutes"],
            timezone=profile["timezone"],
            shift_type=item["shift_type"],
        )
        for item in fixture["shifts"]
    ]
    pay_rates = [
        PayRate(
            hourly_rate=Decimal(item["hourly_rate"]),
            effective_from=datetime.fromisoformat(item["effective_from"]).date(),
            effective_to=(
                datetime.fromisoformat(item["effective_to"]).date()
                if item["effective_to"]
                else None
            ),
        )
        for item in fixture["pay_rates"]
    ]

    summary = calculate_schedule_summary(shifts, pay_rates)
    expected = fixture["summaries"]["2026-09-01:2026-09-30"]

    assert summary.shift_count == expected["shift_count"]
    assert str(summary.total_paid_hours) == expected["total_paid_hours"]
    assert str(summary.estimated_pay) == expected["estimated_pay"]
    assert summary.shift_type_counts == expected["shift_type_counts"]
    assert {
        week_start.isoformat(): str(hours)
        for week_start, hours in summary.weekly_paid_hours.items()
    } == expected["weekly_hours"]
    assert summary.longest_consecutive_days == expected["longest_consecutive_days"]
    assert all(item["source"] == "manual" for item in fixture["shifts"])
