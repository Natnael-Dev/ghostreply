"""contacts.json (project root) maps a name to a phone or chat id."""
import json
import re
from pathlib import Path

CONTACTS_FILE = Path(__file__).resolve().parent.parent / "contacts.json"


def load() -> dict[str, str]:
    try:
        data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def names() -> list[str]:
    return list(load().keys())


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _same_number(a: str, b: str) -> bool:
    # "+15550100000" and "+15550100000" are the same line
    if not (a and b):
        return False
    min_len = min(len(a), len(b))
    return min_len >= 9 and (a.endswith(b) or b.endswith(a))


def namespace_id(channel: str, raw_id: str) -> str:
    """Namespace an ID with its channel prefix (e.g. wa:<id>, tg:<id>)."""
    if raw_id.startswith(f"{channel}:"):
        return raw_id
    return f"{channel}:{raw_id}"


def strip_namespace(id_str: str) -> str:
    """Strip channel namespace prefix if present."""
    if id_str.startswith("wa:") or id_str.startswith("tg:"):
        return id_str.split(":", 1)[1]
    return id_str


def name_for(chat_id: str, number: str | None = None) -> str | None:
    """Reverse lookup: which contacts.json name does this chat belong to?"""
    raw_chat = strip_namespace(chat_id)
    raw_num = strip_namespace(number) if number else None
    base = raw_chat.split("@")[0]
    for name, value in load().items():
        val = strip_namespace(value.strip())
        if "@" in val:
            if val == raw_chat or val.split("@")[0] == base:
                return name
        else:
            d = _digits(val)
            match_base = _same_number(d, _digits(base))
            match_num = _same_number(d, _digits(raw_num or ""))
            if match_base or match_num:
                return name
    return None


def canonical(name: str) -> str | None:
    """Match name case-insensitively and return as written in contacts."""
    mapping = {n.strip().lower(): n for n in names()}
    return mapping.get((name or "").strip().lower())
