#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 PROJECT_ID REGION SERVICE" >&2
  exit 2
fi

project_id="$1"
region="$2"
service="$3"

service_json="$(gcloud run services describe "$service" \
  --project="$project_id" --region="$region" --format=json)"

jq -e '
  .metadata.annotations["run.googleapis.com/launch-stage"] != "BETA" and
  (.spec.template.metadata.annotations["autoscaling.knative.dev/minScale"] // "0") == "0" and
  .spec.template.metadata.annotations["autoscaling.knative.dev/maxScale"] == "1" and
  .spec.template.metadata.annotations["run.googleapis.com/cpu-throttling"] == "true" and
  .spec.template.spec.containerConcurrency == 4 and
  .spec.template.spec.timeoutSeconds == 120 and
  (.spec.template.spec.containers | length) == 1 and
  .spec.template.spec.containers[0].resources.limits.cpu == "1" and
  .spec.template.spec.containers[0].resources.limits.memory == "512Mi" and
  (.spec.template.metadata.annotations["run.googleapis.com/vpc-access-connector"] == null) and
  (.spec.template.metadata.annotations["run.googleapis.com/gpu-zonal-redundancy-disabled"] == null)
' <<<"$service_json" >/dev/null

service_url="$(jq -r '.status.url' <<<"$service_json")"
curl --fail --silent --show-error --retry 5 --retry-delay 2 \
  "$service_url/api/v1/health" | jq -e '.status == "ok"' >/dev/null
curl --fail --silent --show-error --retry 5 --retry-delay 2 \
  "$service_url/" | grep -q "ShiftMate Web"

job_count="$(gcloud scheduler jobs list --project="$project_id" \
  --location="$region" --format='value(name)' | wc -l | tr -d ' ')"
[[ "$job_count" == "1" ]]
gcloud scheduler jobs describe daily-maintenance --project="$project_id" \
  --location="$region" --format='value(name)' | grep -q daily-maintenance

echo "Deployed policy and smoke checks passed: $service_url"
