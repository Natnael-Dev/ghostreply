-- Migration 002: Audit Log Immutability Triggers
-- Prevents UPDATE and DELETE operations on audit log records.

CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
BEFORE UPDATE ON audit
BEGIN
    SELECT RAISE(FAIL, 'Audit log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
BEFORE DELETE ON audit
BEGIN
    SELECT RAISE(FAIL, 'Audit log is append-only');
END;
