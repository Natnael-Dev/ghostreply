# Security Policy

## Supported Versions

Only the current main development branch of `ghostreply` receives security patches.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| < 0.2.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability or sensitive information disclosure in `ghostreply`, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. Send report details privately via GitHub Private Vulnerability Reporting on this repository (`Security` -> `Advisories` -> `Report a vulnerability`).
3. Include:
   - Type of issue (e.g. secret leakage, authentication bypass, injection, memory safety).
   - Exact steps or minimal reproducer.
   - Any suggested mitigations.

You will receive an initial response within 48 hours.

## Security Architecture & Invariants

- **Fail-Closed by Default**: Direct sending and automated replies are disabled by default. Unknown contact modes fall through to `HOLD`.
- **Zero Production Sends Without Owner Approval**: In the current version, `AUTO_SEND` is never emitted. All drafts require explicit human authorization.
- **Append-Only Auditing**: SQLite database triggers block all updates and deletions on audit tables.
- **Local-Only Credential Vault**: MTProto session strings and cryptographic keys are encrypted at rest with Argon2id and AES-256-GCM. Decrypted secrets are kept in memory only and never serialized or logged.
- **Redaction**: All logging pipelines anonymize personal identifiable information (PII) including phone numbers and message content.
