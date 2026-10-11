def test_transition_is_atomic(fresh_db):
    item = fresh_db.add_held("1@c.us", "hi", "hello", reason="needs_owner")
    assert fresh_db.transition(item, "pending", "sending") is True
    assert fresh_db.transition(item, "pending", "sending") is False   # a double click can't send twice
    assert fresh_db.get(item)["status"] == "sending"


def test_pending_only_lists_pending_and_keeps_reason(fresh_db):
    a = fresh_db.add_held("1@c.us", "a", "r", reason="paused")
    b = fresh_db.add_held("2@c.us", "b", "r")
    fresh_db.transition(b, "pending", "dismissed")
    rows = fresh_db.pending()
    assert [r["id"] for r in rows] == [a] and rows[0]["reason"] == "paused"


def test_memory_keeps_only_the_last_messages_in_order(fresh_db):
    for i in range(10):
        fresh_db.add_message("c1", "user", f"m{i}", keep=4)
    fresh_db.add_message("c2", "user", "other", keep=4)
    assert [m["content"] for m in fresh_db.get_messages("c1")] == ["m6", "m7", "m8", "m9"]
    assert len(fresh_db.get_messages("c2")) == 1


def test_contact_modes(fresh_db):
    assert fresh_db.get_mode("Mom") == "hold" and fresh_db.get_mode(None) == "hold"
    fresh_db.set_mode("Mom", "auto")
    assert fresh_db.get_mode("mom") == "auto"          # case-insensitive
    fresh_db.set_mode("Mom", "hold")
    assert fresh_db.all_modes() == {}


def test_kill_switch_defaults_to_off(fresh_db):
    assert fresh_db.auto_reply_enabled() is False
    fresh_db.set_setting("auto_reply", "1")
    assert fresh_db.auto_reply_enabled() is True


def test_old_database_is_migrated(tmp_path, monkeypatch):
    import sqlite3

    from app import db
    path = tmp_path / "old.db"
    sqlite3.connect(path).execute(
        "CREATE TABLE held (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, chat_id TEXT, incoming TEXT, reply TEXT, status TEXT DEFAULT 'pending')"
    ).connection.commit()
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init()
    assert db.get(db.add_held("1@c.us", "a", "b", reason="x"))["reason"] == "x"


def test_message_log_filters_and_order(fresh_db):
    fresh_db.log_message("1@c.us", "Mom", "in", "هتيجي؟", "replied")
    fresh_db.log_message("1@c.us", "Mom", "out", "ايوة", "auto")
    fresh_db.log_message("2@c.us", "Dad", "in", "hi", "held")
    assert [m["body"] for m in fresh_db.query_messages()] == ["hi", "ايوة", "هتيجي؟"]          # newest first
    assert [m["body"] for m in fresh_db.query_messages(name="mom")] == ["ايوة", "هتيجي؟"]      # case-insensitive
    assert [m["body"] for m in fresh_db.query_messages(direction="in", name="Mom")] == ["هتيجي؟"]
    assert fresh_db.query_messages(since=9_999_999_999) == []


def test_message_log_time_window_and_purge(fresh_db):
    import time
    fresh_db.log_message("1@c.us", "Mom", "in", "old", "replied")
    with fresh_db._db() as c:
        c.execute("UPDATE message_log SET ts = ?", (time.time() - 40 * 86400,))
    fresh_db.log_message("1@c.us", "Mom", "in", "new", "replied")
    assert [m["body"] for m in fresh_db.query_messages(since=time.time() - 86400)] == ["new"]
    assert fresh_db.purge_messages(days=30) == 1
    assert [m["body"] for m in fresh_db.query_messages()] == ["new"]


def test_direct_send_defaults_to_off(fresh_db):
    assert fresh_db.direct_send_enabled() is False
    fresh_db.set_setting("direct_send", "1")
    assert fresh_db.direct_send_enabled() is True


def test_failclosed_v1_clamp_behavior(tmp_path, monkeypatch, capsys):
    import sqlite3
    from app import db

    db_file = tmp_path / "clamp_test.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)

    # (a) A pre-seeded DB with auto_reply=1 and direct_send=1 reads 0 after init
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO settings (key, value) VALUES ('auto_reply', '1'), ('direct_send', '1')")
        conn.commit()

    db.init()
    out = capsys.readouterr().out
    assert "[Security] Clamped auto_reply and direct_send to fail-closed defaults" in out
    assert db.auto_reply_enabled() is False
    assert db.direct_send_enabled() is False
    assert db.get_setting("failclosed_v1") == "1"

    # (b) The owner then sets auto_reply=1 and a second init keeps 1
    db.set_setting("auto_reply", "1")
    db.init()
    assert db.auto_reply_enabled() is True

    # (c) A fresh DB gets the marker and defaults
    fresh_file = tmp_path / "fresh_clamp.db"
    monkeypatch.setattr(db, "DB_PATH", fresh_file)
    db.init()
    assert db.auto_reply_enabled() is False
    assert db.direct_send_enabled() is False
    assert db.get_setting("failclosed_v1") == "1"
