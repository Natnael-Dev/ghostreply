"""Encrypted session vault with persistent lockout and memory purge."""
import json
import os
import time
from pathlib import Path
from typing import Optional, Protocol

from app.security.crypto import decrypt_payload, encrypt_payload

DEFAULT_VAULT_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "telegram.session.enc"
)
DEFAULT_STATE_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "vault_lockout.json"
)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900.0  # 15 minutes


class VaultLockedError(Exception):
    """Raised when an operation requires an unlocked session vault."""


class VaultLockoutError(Exception):
    """Raised when unlock attempts exceed limit (5 tries / 15m lockout)."""


class SessionVault(Protocol):
    """Protocol for encrypted credential vault."""

    def is_unlocked(self) -> bool:
        ...

    async def unlock(self, passphrase: str) -> bool:
        ...

    async def lock(self) -> None:
        ...

    async def get_string_session(self) -> str:
        ...

    async def set_string_session(
        self, session_str: str, passphrase: str
    ) -> None:
        ...


class EncryptedSessionVault:
    """Argon2id/Scrypt + AES-256-GCM encrypted credential vault."""

    def __init__(
        self,
        vault_file: Optional[Path] = None,
        state_file: Optional[Path] = None,
    ) -> None:
        self.vault_file = vault_file or DEFAULT_VAULT_FILE
        self.state_file = state_file or DEFAULT_STATE_FILE
        self._memory_buffer: Optional[bytearray] = None
        self._is_unlocked = False

    def is_unlocked(self) -> bool:
        return self._is_unlocked

    async def unlock(self, passphrase: str) -> bool:
        self._check_lockout()

        if not self.vault_file.exists():
            return False

        blob = self.vault_file.read_bytes()
        try:
            decrypted = decrypt_payload(blob, passphrase)
            self._wipe_memory()
            self._memory_buffer = bytearray(decrypted)
            self._is_unlocked = True
            self._reset_lockout_state()
            return True
        except ValueError:
            self._record_failure()
            return False

    async def lock(self) -> None:
        self._wipe_memory()
        self._is_unlocked = False

    async def get_string_session(self) -> str:
        if not self._is_unlocked or self._memory_buffer is None:
            raise VaultLockedError("Session vault is locked")
        return self._memory_buffer.decode("utf-8")

    async def set_string_session(
        self, session_str: str, passphrase: str
    ) -> None:
        self.vault_file.parent.mkdir(parents=True, exist_ok=True)
        raw_bytes = session_str.encode("utf-8")
        blob = encrypt_payload(raw_bytes, passphrase)

        tmp_path = self.vault_file.with_suffix(".tmp")
        tmp_path.write_bytes(blob)
        self._set_file_permissions(tmp_path)
        tmp_path.replace(self.vault_file)
        self._set_file_permissions(self.vault_file)

    def _wipe_memory(self) -> None:
        if self._memory_buffer is not None:
            for i in range(len(self._memory_buffer)):
                self._memory_buffer[i] = 0
            self._memory_buffer = None

    def _check_lockout(self) -> None:
        state = self._load_state()
        lockout_until = state.get("lockout_until", 0.0)
        if time.time() < lockout_until:
            remaining = int(lockout_until - time.time())
            raise VaultLockoutError(
                f"Vault is locked out. Try again in {remaining} seconds."
            )

    def _record_failure(self) -> None:
        state = self._load_state()
        failed = state.get("failed_attempts", 0) + 1
        lockout_until = 0.0
        if failed >= MAX_FAILED_ATTEMPTS:
            lockout_until = time.time() + LOCKOUT_DURATION_SECONDS

        self._save_state({
            "failed_attempts": failed,
            "lockout_until": lockout_until,
        })

        if failed >= MAX_FAILED_ATTEMPTS:
            raise VaultLockoutError(
                "Maximum failed unlock attempts exceeded (15-minute lockout)."
            )

    def _reset_lockout_state(self) -> None:
        self._save_state({"failed_attempts": 0, "lockout_until": 0.0})

    def _load_state(self) -> dict:
        if not self.state_file.exists():
            return {"failed_attempts": 0, "lockout_until": 0.0}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {"failed_attempts": 0, "lockout_until": 0.0}

    def _save_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

    def _set_file_permissions(self, path: Path) -> None:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
