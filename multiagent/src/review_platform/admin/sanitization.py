"""Lam sach du lieu van hanh truoc khi dua vao HTML hoac security audit."""
from collections.abc import Mapping
import re
import unicodedata


REDACTED = "[đã ẩn]"
TRUNCATED = "[đã rút gọn]"
_SENSITIVE_PARTS = (
    "password",
    "token",
    "authorization",
    "cookie",
    "secret",
    "apikey",
)
_HEADER_PATTERN = re.compile(
    r"(?im)\b(authorization|proxy[-_ ]?authorization|cookie|set[-_ ]?cookie|"
    r"x[-_ ]?api[-_ ]?key)\s*:\s*[^\r\n]*"
)
_PAIR_PATTERN = re.compile(
    r"(?i)\b(password|token|secret|api[-_ ]?key)\b\s*[:=]\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    try:
        return str(value)
    except Exception:
        return "[không thể hiển thị]"


def _normalized_key(value) -> str:
    raw = unicodedata.normalize("NFKD", _text(value)).casefold()
    return "".join(character for character in raw if character.isalnum())


def _is_sensitive_key(value) -> bool:
    normalized = _normalized_key(value)
    return any(part in normalized for part in _SENSITIVE_PARTS)


def sanitize_text(value, max_length: int = 1000) -> str:
    """Che credential/header nhay cam truoc khi gioi han do dai."""
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length < 1:
        raise ValueError("max_length phai la so nguyen duong")
    text = _text(value)
    text = _HEADER_PATTERN.sub(lambda match: f"{match.group(1)}: {REDACTED}", text)
    text = _PAIR_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTED}", text)
    text = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", text)
    return text[:max_length]


def sanitize_mapping(value, *, max_depth: int = 3, max_items: int = 50):
    """Tra ve cau truc JSON-safe da redact; legacy sai kieu khong lam 500."""
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 1:
        raise ValueError("max_depth phai la so nguyen duong")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
        raise ValueError("max_items phai la so nguyen duong")

    def visit(current, depth: int):
        if isinstance(current, Mapping):
            if depth >= max_depth:
                return TRUNCATED
            result = {}
            entries = list(current.items())
            for raw_key, nested in entries[:max_items]:
                key = sanitize_text(raw_key, max_length=200)
                result[key] = REDACTED if _is_sensitive_key(raw_key) else visit(
                    nested,
                    depth + 1,
                )
            if len(entries) > max_items:
                result[TRUNCATED] = len(entries) - max_items
            return result
        if isinstance(current, (list, tuple)):
            if depth >= max_depth:
                return TRUNCATED
            result = [visit(item, depth + 1) for item in current[:max_items]]
            if len(current) > max_items:
                result.append(TRUNCATED)
            return result
        if isinstance(current, (str, bytes)):
            return sanitize_text(current)
        if current is None or isinstance(current, (bool, int, float)):
            return current
        return sanitize_text(current)

    return visit(value, 0)
