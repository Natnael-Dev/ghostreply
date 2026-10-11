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
2. Send report details privately via [GitHub Private Vulnerability Reporting](https://github.com/Natnael-Dev/ghostreply/security/advisories/new).
3. If private vulnerability reporting is unavailable or disabled, contact the repository maintainer directly before public disclosure.
4. Include:
   - Type of issue (e.g. secret leakage, authentication bypass, injection, memory safety).
   - Exact steps or minimal reproducer.
   - Any suggested mitigations.

You will receive an initial response within 48 hours.

## Security Architecture & Invariants

- **Fail-Closed by Default**: Direct sending and automated replies are disabled by default (`app/db.py:61-64`). Unknown contact modes fall through to `HOLD` (`app/contacts.py:27`).
- **Zero Production Sends Without Owner Approval**: In the current version, `AUTO_SEND` is never emitted. All drafts require explicit human authorization.
- **Append-Only Auditing**: SQLite database triggers block all updates and deletions on audit tables (`app/db.py:34-44`).
- **Local-Only Credential Vault**: Cryptographic keys and credentials are encrypted at rest with scrypt ($N=16384, r=8, p=1$) and AES-256-GCM (`app/session_vault.py:14-25`). Decrypted secrets are kept in memory only and never serialized or logged.
- **Redaction**: All logging pipelines anonymize personal identifiable information (PII) including phone numbers and message content (`app/log.py:16-25`).
