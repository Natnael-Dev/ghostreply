# ghostreply

A multi-channel, human-in-the-loop personal auto-reply agent.

> **Important Licensing Notice**: The MIT License in this repository applies strictly to original contributions. Files imported from the upstream prototype (listed in [`docs/PROVENANCE.md`](docs/PROVENANCE.md)) originated from an unlicensed upstream repository (`license: null`) and are **not** covered by the license grant while licensing remains unresolved.

> **Core Operating Invariant**: *"Never say something I wouldn't say; hold anything uncertain for owner approval."* The system fails closed.

---

## What It Is

`ghostreply` is an agentic assistant designed to triage incoming personal messages, retrieve grounding facts from owner-provided knowledge files, synthesize polite reply drafts, and require human approval before any outbound transmission.

---

## Status and Honest Limits

- **Status**: Pre-alpha (Active architectural refactoring).
- **Target Mode**: Draft-and-approve. Automated replies are never dispatched autonomously without human review (`AUTO_SEND` is a reserved state and is never emitted).
- **WhatsApp Support**: Operates via an unofficial local bridge (`whatsapp-web.js` on Node.js communicating over localhost with FastAPI).
- **Ban Risk Warning**: Using automated or scripted interaction on WhatsApp via unofficial client libraries carries an inherent risk of account suspension or permanent bans by WhatsApp / Meta.
- **No Telegram Code**: While architectural plans (ADR-001, ADR-002) describe a future Telegram userbot and approval bot topology, **no Telegram integration code exists in this repository**.

---

## Security & Fail-Closed Defaults

- **Fail-Closed Defaults**: Initial database defaults set `auto_reply="0"`, `direct_send="0"`, and `contact_mode="hold"`. Unknown contact modes fall through strictly to hold.
- **One-Time Failclosed Clamp**: At startup, `app.db.init()` inspects `settings` for `failclosed_v1`. If absent, it clamps `auto_reply` and `direct_send` to `"0"`, records the marker, and prevents accidental sends on upgraded legacy databases.
- **Global Kill Switch**: Setting `auto_reply='0'` or `direct_send='0'` (via CLI or dashboard) causes `dispatch_with_rechecks()` to immediately abort and transition approved drafts back to `HELD`.
- **Append-Only Auditing**: SQLite database triggers (`trg_audit_no_update`, `trg_audit_no_delete`) block all modifications and deletions on the audit log.
- **Session Vault**: Secrets and tokens are encrypted at rest using `hashlib.scrypt` ($N=2^{14}, r=8, p=1$) + AES-256-GCM. Unlocked secrets remain in memory only.
