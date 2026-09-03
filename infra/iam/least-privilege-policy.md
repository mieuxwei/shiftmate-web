# Production IAM design

This document describes the production permission boundary; it is not an
instruction to provision resources without reviewing the deployment guide.

| Principal | Scope | Roles / permissions |
| --- | --- | --- |
| `shiftmate-runtime@PROJECT_ID` | Cloud Run service identity | No project role by default. It calls Supabase, Gemini and Google APIs over HTTPS. |
| `scheduler-invoker@PROJECT_ID` | `shiftmate-web` service only | `roles/run.invoker`; its exact email and OIDC audience are also verified by the application. |
| Cloud Scheduler service agent | Project | Google-managed `roles/cloudscheduler.serviceAgent`; do not remove it. |
| GitHub WIF principal | Deploy service account only | `roles/iam.workloadIdentityUser`; restrict the attribute condition to this repository and the protected `main` branch. |
| Deploy service account | Artifact repository | `roles/artifactregistry.writer`. |
| Deploy service account | `shiftmate-web` service | `roles/run.admin`. |
| Deploy service account | Runtime and scheduler service accounts | `roles/iam.serviceAccountUser` on only those two accounts. |
| Deploy service account | `daily-maintenance` job | A custom role containing the required Scheduler get/create/update/pause/delete permissions; use `roles/cloudscheduler.admin` only until that custom role is installed. |

No service-account JSON key is permitted. The public SPA/API service may allow
Cloud Run invocation by `allUsers`; owner data still requires Supabase JWT and
the internal route independently requires a valid Google-signed Scheduler OIDC
token with the configured audience and exact service-account email. This
application check is essential because Cloud Run IAM is service-wide, not
path-specific.

The database login may only `SET ROLE authenticated` for user traffic and
`SET ROLE shiftmate_maintenance` for the one internal endpoint. The maintenance
role is `NOLOGIN`, has no owner impersonation function, and receives narrow
table grants plus explicit RLS policies.
