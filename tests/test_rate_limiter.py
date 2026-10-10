"""Unit tests for RateLimiter and Clock injection (T2)."""
from datetime import datetime, timedelta, timezone
import pytest

from app.approvals.repository import DraftRecord, SqliteDraftRepository
from app.approvals.state import DraftState
from app.channels.rate_limiter import SqliteRateLimiter
from app.gate.prefilter import Clock


class MockClock(Clock):
    """Controllable clock for deterministic rate limit and repository testing."""

    def __init__(self, initial_time: datetime) -> None:
        self._now = initial_time

    def now_utc(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


@pytest.fixture
def mock_clock() -> MockClock:
    return MockClock(datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc))


@pytest.mark.anyio
async def test_fresh_chat_allows_send(tmp_path, mock_clock):
    limiter = SqliteRateLimiter(
        db_path=tmp_path / "rate.db",
        clock=mock_clock,
        cooldown_seconds=60.0,
        global_cap=5,
        global_window_seconds=3600.0,
    )
    assert await limiter.check_limits("wa:chat1") is True


@pytest.mark.anyio
async def test_per_chat_cooldown_blocks_and_expires(tmp_path, mock_clock):
    limiter = SqliteRateLimiter(
        db_path=tmp_path / "rate.db",
        clock=mock_clock,
        cooldown_seconds=60.0,
        global_cap=5,
        global_window_seconds=3600.0,
    )
    await limiter.record_send("wa:chat1")
    assert await limiter.check_limits("wa:chat1") is False
    assert await limiter.check_limits("wa:chat2") is True

    mock_clock.advance(30.0)
    assert await limiter.check_limits("wa:chat1") is False

    mock_clock.advance(31.0)
    assert await limiter.check_limits("wa:chat1") is True


@pytest.mark.anyio
async def test_global_cap_blocks_all_chats_and_expires(tmp_path, mock_clock):
    limiter = SqliteRateLimiter(
        db_path=tmp_path / "rate.db",
        clock=mock_clock,
        cooldown_seconds=5.0,
        global_cap=3,
        global_window_seconds=60.0,
    )
    for i in range(3):
        assert await limiter.check_limits(f"wa:chat_{i}") is True
        await limiter.record_send(f"wa:chat_{i}")

    assert await limiter.check_limits("wa:chat_99") is False

    mock_clock.advance(61.0)
    assert await limiter.check_limits("wa:chat_99") is True


@pytest.mark.anyio
async def test_clock_injection_in_sqlite_draft_repository(tmp_path, mock_clock):
    repo = SqliteDraftRepository(
        db_path=tmp_path / "drafts.db",
        clock=mock_clock,
    )
    draft = DraftRecord(
        draft_id=101,
        channel="wa",
        sender_id="wa:123",
        chat_id="wa:123",
        inbound_message_id="msg-101",
        inbound_text="hello",
        draft_text="hi there",
        status=DraftState.HELD,
        token_hash="hash1",
        draft_hash="hash2",
        reason_codes=["NEEDS_OWNER"],
        created_at=mock_clock.now_utc(),
        updated_at=mock_clock.now_utc(),
    )
    await repo.create_held_draft(draft)
    mock_clock.advance(120.0)

    transitioned = await repo.transition_state(
        draft_id=101,
        expected_state=DraftState.HELD,
        new_state=DraftState.APPROVED,
    )
    assert transitioned is True

    updated = await repo.get_draft(101)
    assert updated is not None
    assert updated.status == DraftState.APPROVED
    assert updated.updated_at == mock_clock.now_utc()
