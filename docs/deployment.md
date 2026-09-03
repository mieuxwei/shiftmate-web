# Production deployment

The production target is one Cloud Run service in `asia-east1` inside the
dedicated `my-shiftmate-web-prod-95939` project. Artifact Registry is
co-located, the service scales from zero to at most one instance, and GitHub
uses Workload Identity Federation instead of a service-account key.

## Resource inventory

| Resource | Name | Cost boundary |
| --- | --- | --- |
| Artifact Registry | `asia-east1/shiftmate-web` | Keep production plus one rollback digest; scanning disabled. |
| Cloud Run | `shiftmate-web` | Request-based, min 0, max 1, 1 CPU, 512 MiB, no GPU or VPC connector. |
| Cloud Scheduler | `daily-maintenance` | Exactly one job, daily, authenticated with OIDC. |
| Service accounts | `shiftmate-runtime`, `scheduler-invoker`, `shiftmate-deploy` | No user-managed keys. |
| WIF | `github/shiftmate-web` | Only `mieuxwei/shiftmate-web` on `refs/heads/main`. |

The canonical non-secret identifiers are in
`infra/deployment/production.json`. Never place a database URL, API key,
OAuth client secret, encryption key, or token in that file.

## Bootstrap

Run `infra/deployment/bootstrap.sh` as a project owner from an authenticated
Cloud Shell. The script is idempotent: it enables only the required APIs,
creates the three service accounts, creates the regional Docker repository,
applies the two-version cleanup policy, installs the narrow Scheduler deployer
role, and configures branch-restricted GitHub WIF.

The first Cloud Run service is created once by the project owner. After it
exists, grant `roles/run.admin` on that service—not the project—to
`shiftmate-deploy`, and grant `roles/run.invoker` on that service to
`scheduler-invoker`. The release workflow can then update the service and its
IAM policy without project-wide Cloud Run administration.

The deployment uses six or fewer active Secret Manager versions:

1. `runtime-database-url`
2. `migration-database-url`
3. `gemini-api-key`
4. `google-oauth-client-secret`
5. `google-oauth-state-secret`
6. `calendar-token-encryption-key`

Grant the runtime identity accessor only on secrets 1, 3, 4, 5, and 6. Grant
the deploy identity accessor only on secret 2. Create no service-account key.

## GitHub production configuration

Create a `production` environment and set these repository environment
variables:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_ARTIFACT_REPOSITORY`
- `GCP_CLOUD_RUN_SERVICE`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_SCHEDULER_SERVICE_ACCOUNT`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`

The release job is triggered only after `Validate` succeeds for a push to
`main`, or by an explicit dispatch from `main`. It checks out the exact
validated SHA, authenticates through WIF, upgrades the production schema,
pushes immutable and `production` image tags, deploys, reconciles the one
Scheduler job, and runs policy plus HTTP smoke checks.

## Production migrations

`migration-database-url` is the Supabase owner connection through the shared
session pooler and is used only by the short-lived IPv4 GitHub release runner.
`runtime-database-url` is the bounded transaction-pooler login without owner or
`BYPASSRLS` privileges. The release runner masks the migration URL before
invoking `alembic upgrade head`.

Every migration must remain backwards compatible with the currently deployed
revision because the schema upgrade finishes before Cloud Run moves traffic to
the new image. A failed deploy does not trigger an automatic downgrade.

## Verification

The release workflow runs `scripts/verify_deployment.sh`. It verifies the
deployed CPU, memory, concurrency, timeout, CPU throttling, min/max scaling,
single container, absent VPC connector/GPU configuration, health endpoint,
SPA response, and exactly one Scheduler job. Also inspect:

```bash
gcloud artifacts docker images list \
  asia-east1-docker.pkg.dev/my-shiftmate-web-prod-95939/shiftmate-web \
  --include-tags
gcloud iam service-accounts keys list \
  --iam-account=shiftmate-deploy@my-shiftmate-web-prod-95939.iam.gserviceaccount.com
```

The service-account key list must contain no user-managed key.

## Rollback

Read-only review first:

```bash
gcloud run revisions list --service=shiftmate-web --region=asia-east1
gcloud artifacts docker images list \
  asia-east1-docker.pkg.dev/my-shiftmate-web-prod-95939/shiftmate-web \
  --include-tags
```

After identifying the previously verified revision, route all traffic to that
exact revision:

```bash
gcloud run services update-traffic shiftmate-web \
  --region=asia-east1 --to-revisions=VERIFIED_REVISION=100
```

Do not downgrade the database automatically. Forward-fix migrations unless an
independently reviewed downgrade is explicitly approved.

## Stop and teardown dry-run

Inventory before any destructive operation:

```bash
gcloud scheduler jobs list --location=asia-east1
gcloud run services describe shiftmate-web --region=asia-east1
gcloud artifacts repositories describe shiftmate-web --location=asia-east1
gcloud iam service-accounts list --filter='email~shiftmate'
gcloud iam workload-identity-pools list --location=global
```

Emergency stop order: pause `daily-maintenance`, set the service maximum to
zero, remove public and Scheduler invokers, then verify no new requests can
start. Permanent teardown order: delete the Scheduler job, Cloud Run service,
Artifact Registry repository, six application secrets, WIF provider/pool,
custom Scheduler role, and finally the three service accounts. Each delete
requires a fresh inventory and explicit approval; never use wildcard targets.
