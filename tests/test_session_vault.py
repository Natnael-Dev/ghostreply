import pytest
from pathlib import Path

from app.security.vault import (
    EncryptedSessionVault,
    VaultLockedError,
    VaultLockoutError,
)


@pytest.fixture
def vault_dir(tmp_path: Path):
    v_file = tmp_path / "telegram.session.enc"
    state_file = tmp_path / "vault_state.json"
    return v_file, state_file


@pytest.mark.anyio
async def test_vault_encrypt_decrypt_lifecycle(vault_dir):
    v_file, state_file = vault_dir
    vault = EncryptedSessionVault(vault_file=v_file, state_file=state_file)

    assert vault.is_unlocked() is False
    with pytest.raises(VaultLockedError):
        await vault.get_string_session()

    raw_session = "1Bff4abc_dummy_telethon_string_session_998877"
    passphrase = "correct_master_password_123"

    # Set new encrypted session
    await vault.set_string_session(raw_session, passphrase)
    assert v_file.exists()

    # Before unlock, still locked
    assert vault.is_unlocked() is False

    # Unlock with wrong password fails
    success = await vault.unlock("wrong_password")
    assert success is False
    assert vault.is_unlocked() is False

    # Unlock with correct password succeeds
    success = await vault.unlock(passphrase)
    assert success is True
    assert vault.is_unlocked() is True

    # Retrieve decrypted string session
    retrieved = await vault.get_string_session()
    assert retrieved == raw_session

    # Lock purges memory
    await vault.lock()
    assert vault.is_unlocked() is False
    with pytest.raises(VaultLockedError):
        await vault.get_string_session()


@pytest.mark.anyio
async def test_vault_persistent_lockout_trigger(vault_dir):
    v_file, state_file = vault_dir
    vault = EncryptedSessionVault(vault_file=v_file, state_file=state_file)

    await vault.set_string_session("secret_session", "good_pass")

    # Fail 4 times: returns False
    for _ in range(4):
        assert await vault.unlock("bad_pass") is False

    # 5th failure: triggers persistent lockout
    with pytest.raises(VaultLockoutError):
        await vault.unlock("bad_pass")

    # Lockout survives process restart / new vault instance
    new_vault_instance = EncryptedSessionVault(
        vault_file=v_file, state_file=state_file
    )
    with pytest.raises(VaultLockoutError):
        await new_vault_instance.unlock("good_pass")


@pytest.mark.anyio
async def test_file_format_has_no_plaintext(vault_dir):
    v_file, state_file = vault_dir
    vault = EncryptedSessionVault(vault_file=v_file, state_file=state_file)

    secret = "SUPER_SECRET_TOKEN_DO_NOT_LEAK"
    await vault.set_string_session(secret, "pw")

    raw_bytes = v_file.read_bytes()
    assert secret.encode() not in raw_bytes
    assert b"GR1" == raw_bytes[:3]  # Header tag
