# Zero-cost operations runbook

Last policy check: 2026-09-03. This runbook is a deployment design only. M9
created no GCP resource, used no live credential, and enabled no paid feature.

## Hard deployment envelope

The versioned source of truth is
`infra/cloud-run/service-policy.json`: one container, request-based billing
(`cpuThrottling=true`), 1 vCPU, 512 MiB, concurrency 4, 120-second timeout,
minimum instances 0, maximum instances 1, no GPU, and no VPC connector. Raising
any limit or adding a resource requires explicit approval. The API also applies
a per-peer 120 request/minute limiter, 5 MiB/40-page file limits, 10 uploads per
owner per day, and a durable application-wide cap of 50 Gemini requests/day.

Cloud Run documents that request-based billing charges while requests are being
processed and during startup/shutdown; min 0 permits scale-to-zero. GPU requires
instance-based billing, so it is prohibited here:

- https://docs.cloud.google.com/run/docs/configuring/billing-settings
- https://docs.cloud.google.com/run/docs/configuring/min-instances
- https://docs.cloud.google.com/run/docs/configuring/services/gpu
- https://docs.cloud.google.com/run/docs/configuring/vpc-connectors

## Resource inventory and controls

| Resource | Planned count | Free/cost boundary | Usage check | Cleanup |
| --- | ---: | --- | --- | --- |
| Cloud Run service | 1 | Request-based free allowance is account-scoped and usage-dependent. | Billing report plus Cloud Run request, CPU and memory metrics weekly. | Set max instances to 0 for an incident; delete the service to stop it permanently. |
| Artifact Registry regional Docker repository | 1 | First 0.5 GiB-month per billing account is currently free. | Repository size before and after every release; stop before push if production plus rollback could reach 0.5 GiB. | Dry-run then activate the versioned cleanup policy; keep at most current production and one rollback image. Delete the repository for teardown. |
| Cloud Scheduler job | 1 | Three jobs/month per billing account are currently free; paused jobs still count. | List all jobs across projects on the billing account before creation and monthly. | Pause for an incident; delete for teardown. Never add a second ShiftMate job without approval. |
| Cloud IAM service accounts | 3 | No standalone charge, but permissions can authorize charged resources. | Quarterly IAM policy review and after every deployment change. | Disable, remove bindings, then delete after dependent resources are gone. |
| Budget notification | 1 | Alerting is not a hard cap. | Confirm recipients and thresholds at 50%, 80%, 100%, and a minimal currency amount after billing is linked. | Keep until all resources and residual charges are verified gone. |
| Cloud Billing spend cap | 1 if eligible | Preview and limited to eligible services; enforcement is not instantaneous. | Check Billing > Budgets & alerts for Cloud Run eligibility before deploy. | Keep enabled; lifting it requires explicit approval. |

Official current references:

- https://cloud.google.com/run/pricing
- https://cloud.google.com/artifact-registry/pricing
- https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy
- https://cloud.google.com/scheduler/pricing
- https://docs.cloud.google.com/scheduler/docs/http-target-auth
- https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps

Free allowances are billing-account-wide, not a guarantee of a zero invoice.
Network egress, builds, stored layers, and use by other projects can consume the
allowance. Check the actual billing account before provisioning.

## Artifact storage policy

`infra/artifact-registry/cleanup-policy.json` deletes versions older than one
day while preserving the two newest versions per package. Apply it as a dry run
first and inspect its audit result after the documented background evaluation
period. Activate deletion only when the candidates leave the deployed image and
one known-good rollback image. Do not enable billable vulnerability scanning.

Before every push:

1. Build the exact production image and record its local compressed/virtual size.
2. List repository images and total bytes.
3. Confirm the projected current-plus-rollback total is below 0.5 GiB. The
   operational warning threshold is 0.40 GiB; at or above it, stop and clean up.
4. Confirm the cleanup policy is active and no extra package is present.

## Scheduler and OIDC

There is exactly one job, `daily-maintenance`, at 03:15 Asia/Taipei. It calls
`POST /api/v1/internal/daily-maintenance` with OIDC. The application verifies
Google's signature, issuer, audience, verified email, job name, and schedule
time before using the `shiftmate_maintenance` database role. A unique
`(job_name, logical_run_date)` claim makes retries no-ops. Work is limited to
expired import cleanup, stale status cleanup, quota-row cleanup, and audit-log
retention; it never performs embeddings or long-running AI work.

## Budget and pre-deploy checklist

- [ ] Use a dedicated GCP project and confirm no unrelated project consumes the
  same account-wide allowances.
- [ ] Confirm Cloud Run, Artifact Registry, and Scheduler pricing again.
- [ ] Create a minimal monthly budget with 50%, 80%, and 100% notifications to
  project owners and billing administrators.
- [ ] If the preview is available, create a Cloud Run spend-cap budget at the
  lowest accepted amount; do not rely on either alert or cap alone.
- [ ] Verify request-based billing, min 0, max 1, no GPU, no VPC connector and
  one container from the deployed service description.
- [ ] Verify exactly one Scheduler job and its dedicated OIDC identity.
- [ ] Verify Artifact Registry storage below 0.40 GiB and scanning disabled.
- [ ] Confirm Supabase and Gemini remain Free Tier and Google Calendar usage is
  demo-scale; retain ICS as the fallback.
- [ ] Review the Billing report immediately after deploy and weekly during the
  public demo.

## Incident stop and teardown

These are review steps for M11; resolve exact project, region, service and
repository names with read-only `describe`/`list` commands before deletion.

1. Pause `daily-maintenance` and set the Cloud Run service maximum instance
   count to zero to stop new compute while preserving configuration.
2. Remove public and Scheduler invoker bindings.
3. Delete the Scheduler job, then the Cloud Run service.
4. Confirm no revision or tagged traffic remains. Delete repository images,
   then the Artifact Registry repository.
5. Remove WIF provider bindings, disable/delete the three service accounts, and
   disable APIs that no other approved resource uses.
6. Keep the budget active until Billing reports zero residual usage and the
   repository size is zero. Record the final report and only then remove it.

Never create Cloud SQL, Cloud Storage, Load Balancer, Cloud NAT, Serverless VPC
Access, GPU, or a second scheduler job for this project without explicit
approval.
