# ADR 0004: Calendar OAuth and idempotent sync boundary

- Status: Accepted
- Date: 2026-09-02

## Context

The application needs optional Google Calendar synchronization without making Google an
authority for confirmed shifts. OAuth callback requests do not carry the
Supabase bearer token, refresh tokens are long-lived secrets, and retries must
not create duplicate events. The application must still work without Google
credentials.

## Decision

- Use the web-server authorization-code flow with PKCE, a ten-minute encrypted
  HttpOnly `SameSite=Lax` state cookie, exact state comparison, and a local-only
  validated return path.
- Request offline, incremental authorization only when the user chooses the
  Calendar feature. Request the narrow
  `https://www.googleapis.com/auth/calendar.events.owned` scope.
- Keep OAuth client credentials, the state secret, and the distinct refresh
  token encryption key in environment/platform secret stores. Persist only an
  authenticated ciphertext for the refresh token; access tokens remain
  request-local.
- Serialize sync per owner by locking the connection row. Derive a stable,
  provider-valid event ID from owner and shift IDs, insert with that ID, and
  update on conflict. This makes an uncertain create safe to retry.
- Convert a synced record to a tombstone before deleting its confirmed shift.
  The tombstone retains the external event ID and can retry provider deletion.
- Provider errors update only connection/sync metadata. They never write,
  revert, or delete confirmed shift truth.
- Generate RFC 5545 `.ics` output directly from owner-scoped confirmed shifts,
  regardless of OAuth configuration or connection status.

## Consequences

The callback can restore the owner context only after decrypting and validating
the short-lived state cookie. Key rotation requires an explicit token
re-encryption/reconnection procedure. Calendar event descriptions intentionally
contain only the shift type, times, optional notes, and a private synthetic
shift identifier; users should still avoid private data in this portfolio app.
No Google credential or live provider call is needed for tests or ICS export.

## References

- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth)
- [Google Calendar events.insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert)
