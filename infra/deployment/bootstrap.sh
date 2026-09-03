#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
config_file="$root_dir/infra/deployment/production.json"
cleanup_policy="$root_dir/infra/artifact-registry/cleanup-policy.json"
scheduler_role="$root_dir/infra/iam/scheduler-deployer-role.yaml"

project_id="$(jq -r '.projectId' "$config_file")"
project_number="$(jq -r '.projectNumber' "$config_file")"
region="$(jq -r '.region' "$config_file")"
repository="$(jq -r '.artifactRepository' "$config_file")"
github_repository="$(jq -r '.githubRepository' "$config_file")"
runtime_sa="$(jq -r '.runtimeServiceAccount' "$config_file")"
scheduler_sa="$(jq -r '.schedulerServiceAccount' "$config_file")"
deploy_sa="$(jq -r '.deployServiceAccount' "$config_file")"
pool="$(jq -r '.workloadIdentityPool' "$config_file")"
provider="$(jq -r '.workloadIdentityProvider' "$config_file")"

for command in gcloud jq; do
  command -v "$command" >/dev/null || {
    echo "$command is required" >&2
    exit 1
  }
done

gcloud config set project "$project_id"
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  iamcredentials.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  sts.googleapis.com \
  --project="$project_id"

create_service_account() {
  local email="$1"
  local account_id="${email%%@*}"
  local display_name="$2"
  if ! gcloud iam service-accounts describe "$email" \
    --project="$project_id" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$account_id" \
      --project="$project_id" --display-name="$display_name"
  fi
}

create_service_account "$runtime_sa" "ShiftMate runtime"
create_service_account "$scheduler_sa" "ShiftMate scheduler invoker"
create_service_account "$deploy_sa" "ShiftMate GitHub deployer"

if ! gcloud artifacts repositories describe "$repository" \
  --project="$project_id" --location="$region" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$repository" \
    --project="$project_id" \
    --location="$region" \
    --repository-format=docker \
    --description="ShiftMate production and one rollback image" \
    --disable-vulnerability-scanning
fi
gcloud artifacts repositories set-cleanup-policies "$repository" \
  --project="$project_id" --location="$region" --policy="$cleanup_policy"

role_id="shiftmateSchedulerDeployer"
if gcloud iam roles describe "$role_id" --project="$project_id" \
  >/dev/null 2>&1; then
  gcloud iam roles update "$role_id" --project="$project_id" \
    --file="$scheduler_role"
else
  gcloud iam roles create "$role_id" --project="$project_id" \
    --file="$scheduler_role"
fi

if ! gcloud iam workload-identity-pools describe "$pool" \
  --project="$project_id" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$pool" \
    --project="$project_id" --location=global \
    --display-name="GitHub Actions"
fi

if ! gcloud iam workload-identity-pools providers describe "$provider" \
  --project="$project_id" --location=global \
  --workload-identity-pool="$pool" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$provider" \
    --project="$project_id" \
    --location=global \
    --workload-identity-pool="$pool" \
    --display-name="mieuxwei/shiftmate-web main" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='$github_repository' && assertion.ref=='refs/heads/main'"
fi

pool_name="projects/$project_number/locations/global/workloadIdentityPools/$pool"
github_principal="principalSet://iam.googleapis.com/$pool_name/attribute.repository/$github_repository"
gcloud iam service-accounts add-iam-policy-binding "$deploy_sa" \
  --project="$project_id" \
  --role=roles/iam.workloadIdentityUser \
  --member="$github_principal"

for target_sa in "$runtime_sa" "$scheduler_sa"; do
  gcloud iam service-accounts add-iam-policy-binding "$target_sa" \
    --project="$project_id" \
    --role=roles/iam.serviceAccountUser \
    --member="serviceAccount:$deploy_sa"
done

gcloud artifacts repositories add-iam-policy-binding "$repository" \
  --project="$project_id" --location="$region" \
  --role=roles/artifactregistry.writer \
  --member="serviceAccount:$deploy_sa"
gcloud projects add-iam-policy-binding "$project_id" \
  --role="projects/$project_id/roles/$role_id" \
  --member="serviceAccount:$deploy_sa"
gcloud projects add-iam-policy-binding "$project_id" \
  --role=roles/serviceusage.serviceUsageConsumer \
  --member="serviceAccount:$deploy_sa"

echo "Bootstrap complete for $project_id in $region"
echo "WIF provider: $pool_name/providers/$provider"
