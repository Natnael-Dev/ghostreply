# ghostreply

A multi-channel, human-in-the-loop personal auto-reply agent.

> **Core Operating Invariant**: *"Never say something I wouldn't say; hold anything uncertain for owner approval."* The system fails closed.

---

## Project Status

- **Status**: Pre-alpha (Active Development)
- **WhatsApp**: Working (via local Node.js bridge using `whatsapp-web.js`).
- **Telegram**: In progress (Telethon MTProto userbot + supervised Approval Bot).

---

## ⚠️ Unofficial Client Risk Warning

**Important Notice**: `ghostreply` operates via unofficial client mechanisms:
1. **WhatsApp**: Uses `whatsapp-web.js` running headless Chromium locally.
2. **Telegram**: Uses an MTProto userbot (`Telethon`) connecting to personal account credentials.

Both mechanisms are **unofficial third-party clients** and violate WhatsApp and Telegram terms of service for automated activity. Utilizing automated replies on personal accounts carries a real risk of account restriction, temporary suspension, or permanent ban. This project is designed strictly as a personal, single-owner research tool with strict rate-limiting, human-like delays, and fail-closed human approval gates.

---

## Key Principles & Design

- **Fail-Closed Conjunction**: Autonomous sends occur if and only if all conditions in the safety gate evaluate to true. If any check fails, the reply is held.
- **Hold-Only Verifier**: Automated checks can only force a `HOLD`; no check can ever override a `HOLD`. Only explicit owner action can approve a draft.
- **Auditability**: All state transitions produce append-only audit records.
- **In-Memory Sessions**: MTProto credentials are decrypted into memory at runtime and encrypted at rest with Argon2id + AES-256-GCM. Session unlock is local-only.

---

## Attribution & Provenance

`ghostreply` originates from an open-source WhatsApp assistant agent prototype built with a Node bridge, Python FastAPI, LangGraph, and a vanilla-JS dashboard. Architectural concepts and foundational baseline code are derived from that original prototype with full authorization and ownership continuity.
