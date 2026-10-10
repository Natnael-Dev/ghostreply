"""Language detection module enforcing English-only policy with Ge'ez check."""
import re
from typing import Tuple

GEEZ_REGEX = re.compile(r"[\u1200-\u137F]")

SHORT_ENGLISH_TOKENS = {
    "ok",
    "k",
    "okay",
    "yes",
    "yeah",
    "yep",
    "no",
    "nope",
    "thanks",
    "thx",
    "thank you",
    "sure",
    "cool",
    "gm",
    "gn",
    "see you",
    "bye",
    "will do",
    "sounds good",
    "done",
    "got it",
}

COMMON_ENGLISH_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "is", "are", "was", "were", "been",
}


def detect_language(text: str) -> Tuple[str, float, bool]:
    """Analyze incoming text.

    Returns: (detected_language, confidence, has_geez_chars)
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return "en", 1.0, False

    has_geez = bool(GEEZ_REGEX.search(clean_text))
    if has_geez:
        return "am", 0.99, True

    lower = clean_text.lower()
    if lower in SHORT_ENGLISH_TOKENS:
        return "en", 0.95, False

    # Check ASCII / Latin coverage
    ascii_chars = sum(1 for c in clean_text if ord(c) < 128)
    total_chars = len(clean_text)
    ascii_ratio = ascii_chars / total_chars if total_chars > 0 else 1.0

    if ascii_ratio < 0.7:
        return "unknown", 0.4, False

    # Check vocabulary matches
    words = [re.sub(r"[^\w]", "", w) for w in lower.split()]
    words = [w for w in words if w]
    if not words:
        return "en", 0.8, False

    match_count = sum(1 for w in words if w in COMMON_ENGLISH_WORDS)
    ratio = match_count / len(words)

    if ratio >= 0.2 or len(words) <= 3:
        confidence = min(0.95, 0.6 + ratio * 0.4)
        return "en", confidence, False

    return "unknown", 0.5, False
