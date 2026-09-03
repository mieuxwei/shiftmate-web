#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).parents[1]
PRODUCTION_CONFIG = ROOT / "infra/deployment/production.json"
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
DOCKERFILE = ROOT / "Dockerfile"
BOOTSTRAP = ROOT / "infra/deployment/bootstrap.sh"

REQUIRED_ENVIRONMENT = (
    "PROJECT_ID",
    "REGION",
    "REPOSITORY",
    "SERVICE",
    "RUNTIME_SERVICE_ACCOUNT",
    "SCHEDULER_SERVICE_ACCOUNT",
)


def validate_files() -> None:
    config = json.loads(PRODUCTION_CONFIG.read_text(encoding="utf-8"))
    assert config["region"] == "asia-east1"
    assert config["billing"] == "request-based"
    assert config["minInstances"] == 0
    assert config["maxInstances"] == 1
    assert config["gpu"] is False
    assert config["vpcConnector"] is None

    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    required_workflow_tokens = (
        "id-token: write",
        "google-github-actions/auth@v3",
        "workload_identity_provider:",
        "--min-instances=0",
        "--max-instances=1",
        "--cpu-throttling",
        "--no-cpu-boost",
        '--set-env-vars="^~^',
        '--update-env-vars="^~^',
        "DATABASE_URL=runtime-database-url:latest",
        "alembic upgrade head",
        "scripts/verify_m11_deployment.sh",
    )
    for token in required_workflow_tokens:
        assert token in workflow, f"release workflow is missing {token}"
    assert "credentials_json" not in workflow
    assert '--set-env-vars="^@^' not in workflow
    assert '--update-env-vars="^@^' not in workflow
    assert "--vpc-connector" not in workflow
    assert "--gpu" not in workflow

    verifier = (ROOT / "scripts/verify_m11_deployment.sh").read_text(encoding="utf-8")
    assert '["autoscaling.knative.dev/minScale"] // "0"' in verifier

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG VITE_SUPABASE_URL" in dockerfile
    assert "ARG VITE_SUPABASE_ANON_KEY" in dockerfile

    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    assert "refs/heads/main" in bootstrap
    assert "roles/iam.workloadIdentityUser" in bootstrap
    assert "roles/artifactregistry.writer" in bootstrap
    assert "roles/serviceusage.serviceUsageConsumer" in bootstrap
    assert "--disable-vulnerability-scanning" in bootstrap
    assert "service-account keys create" not in bootstrap
    assert "roles/owner" not in bootstrap


def validate_environment() -> None:
    missing = [name for name in REQUIRED_ENVIRONMENT if not os.environ.get(name)]
    assert not missing, f"missing release configuration: {', '.join(missing)}"
    assert os.environ["REGION"] == "asia-east1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", action="store_true")
    args = parser.parse_args()
    validate_files()
    if args.environment:
        validate_environment()
    print("M11 release configuration is valid")


if __name__ == "__main__":
    main()
