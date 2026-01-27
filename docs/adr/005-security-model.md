# ADR-005: Security Model

## Status

Accepted.

## Context

OMEN exposes an HTTP API and may send signals to external webhooks. We need:

1. Authentication for API access
2. Protection against abuse (rate limiting)
3. Safe handling of sensitive data (redaction, no leakage in responses)
4. Auditability of security-relevant events

## Decision

### Authentication

- **Primary:** API key via `X-API-Key` header. Keys are configured in `OMEN_SECURITY_API_KEYS` (comma-separated).
- **Optional:** JWT via `Authorization: Bearer <token>`, gated by `OMEN_SECURITY_JWT_ENABLED` and `OMEN_SECURITY_JWT_SECRET`.
- All protected routes depend on `verify_api_key` (or JWT when enabled). Missing or invalid credentials return `401 Unauthorized`.

### Rate limiting

- In-memory token-bucket per client identifier (e.g. API key or IP when no key).
- Configurable via `OMEN_SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE` and `OMEN_SECURITY_RATE_LIMIT_BURST`.
- When exceeded: `429 Too Many Requests` and `Retry-After` header.
- Rate-limit events are logged for audit.

### Input validation and sanitization

- Request bodies and query params are validated with Pydantic.
- A security validation layer provides `sanitize_string` / `sanitize_dict` to reject or trim dangerous input (e.g. script tags, excessive nesting).
- `SecureEventInput` and similar types constrain event ingestion for webhooks or internal APIs.

### Output redaction

- **`OMEN_SECURITY_REDACT_INTERNAL_FIELDS`:** When enabled, internal-only fields are stripped or summarized before sending to webhooks or external consumers.
- Explanation chains can be reduced to a short summary for external use; full chains stay internal for debugging and audit.

### Webhook signatures

- Outbound webhooks can include an HMAC-SHA256 signature when `OMEN_SECURITY_WEBHOOK_SECRET` is set.
- Recipients can verify payload integrity using the same secret.

### Audit logging

- Security-relevant events (auth success/failure, rate-limit hits, signal access, etc.) are written to a dedicated audit log (e.g. `AuditLogger`), in a structured format suitable for SIEM or compliance review.
- Logs do not include raw secrets or full API keys.

### CORS

- CORS is configurable via `OMEN_SECURITY_CORS_ENABLED` and `OMEN_SECURITY_CORS_ORIGINS`. Defaults support development while allowing locking down in production.

## Consequences

### Positive

- Clear, consistent auth and rate limiting for the API.
- Redaction and validation reduce risk of injection and data leakage.
- Audit trail supports compliance and incident response.

### Negative

- In-memory rate limiting does not scale across multiple API instances; production may need Redis or similar.
- JWT and webhook secrets must be managed securely (e.g. secrets manager, not plain `.env` in repos).

## Notes

Security configuration is centralized in `infrastructure/security/config.py`. Middleware and route dependencies are wired in `main.create_app()`.
