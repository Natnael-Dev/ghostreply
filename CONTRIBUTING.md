# Contributing Guidelines

Thank you for contributing to `ghostreply`!

## Architectural & Safety Invariants

Every contribution must honor our fundamental safety invariants:
1. **Never auto-send**: The system operates strictly human-in-the-loop. `AUTO_SEND` is a reserved token and must not be emitted.
2. **Fail closed**: Defaults must always be disabled (`auto_reply` = 0, `direct_send` = 0, contact mode = `hold`).
3. **No circular imports**: Cross-lane dependencies must communicate via `app/contracts/`. Modules in `app/gate`, `app/channels`, `app/approvals`, and `app/security` must not import across lane boundaries.
4. **Append-only audit logs**: Never modify or delete audit log entries.
5. **No PII in commits or logs**: Never commit phone numbers, personal message text, session tokens, or credentials.

## Development Workflow

1. **Branches and PRs**:
   - Create focused branches for each logical change.
   - PR titles must be descriptive and follow project standards.
   - Never push directly to `main`.
2. **Commit Messages**:
   - Short, lowercase, human, imperative verbs (e.g. `add migration for held reason and number columns`, `repoint channels to contracts`).
   - No prefixes like `feat:`, `fix:`, or `chore:`.
   - No AI footers or tool signatures.
3. **Testing**:
   - The entire test suite must pass before submitting a PR:
     ```bash
     python -m pytest
     ```
   - New functionality requires corresponding unit and integration tests.
4. **Secrets & Privacy Scanning**:
   - Run `python scripts/scan_secrets.py` to ensure no keys or pattern disclosures are introduced.
