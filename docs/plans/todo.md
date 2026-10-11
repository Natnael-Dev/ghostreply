# Phase 7 Remaining Wiring & Shim Removal

## TODO Items

1. **main.py Direct Contract Wiring**:
   - Re-wire `app/main.py` entrypoints to consume `app.contracts` protocols directly rather than relying on legacy module shims.
   - Inject dependencies (`DraftRepository`, `InboundLedger`, `RateLimiter`) at the application composition root.

2. **Legacy Shim Deprecation & Removal**:
   - Remove backwards-compatibility re-export shims in:
     - `app/approvals/state.py`
     - `app/approvals/repository.py`
     - `app/channels/events.py`
     - `app/gate/models.py`
     - `app/gate/prefilter.py`
   - Update any remaining downstream consumers to import directly from `app.contracts.*`.
