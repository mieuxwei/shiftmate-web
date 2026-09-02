#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SERVICE_POLICY = ROOT / "infra/cloud-run/service-policy.json"
CLEANUP_POLICY = ROOT / "infra/artifact-registry/cleanup-policy.json"
SCHEDULER_POLICY = ROOT / "infra/scheduler/daily-maintenance.json"


def main() -> None:
    service = json.loads(SERVICE_POLICY.read_text(encoding="utf-8"))
    assert service["billing"] == "request-based"
    assert service["cpuThrottling"] is True
    assert service["minInstances"] == 0
    assert service["maxInstances"] == 1
    assert service["gpu"] is False
    assert service["vpcConnector"] is None
    assert service["containers"] == 1

    cleanup = json.loads(CLEANUP_POLICY.read_text(encoding="utf-8"))
    keep = [item for item in cleanup if item["action"]["type"] == "Keep"]
    assert len(keep) == 1
    assert keep[0]["mostRecentVersions"]["keepCount"] == 2
    assert any(item["action"]["type"] == "Delete" for item in cleanup)

    scheduler = json.loads(SCHEDULER_POLICY.read_text(encoding="utf-8"))
    assert scheduler["name"] == "daily-maintenance"
    assert scheduler["httpMethod"] == "POST"
    assert scheduler["oidc"]["audience"].startswith("https://")
    assert scheduler["description"].startswith("Idempotent cleanup")
    print("M9 configuration policy is valid")


if __name__ == "__main__":
    main()
