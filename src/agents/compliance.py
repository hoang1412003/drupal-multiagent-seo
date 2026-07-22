import json
import os

_RULES_PATH = os.path.join(os.path.dirname(__file__), "compliance_rules.json")

_rules_cache = None


def _load_rules() -> list[dict]:
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)["phrases"]
    return _rules_cache


def match_blacklist(text: str) -> list[dict]:
    """So khớp cứng (không phân biệt hoa/thường) với danh sách từ cấm.

    Mỗi cụm khớp tạo 1 flag severity "critical" (xem
    docs/superpowers/specs/2026-07-22-compliance-agent-design.md mục 4).
    """
    text_lower = text.lower()
    flags = []
    for rule in _load_rules():
        phrase = rule["text"].lower()
        idx = text_lower.find(phrase)
        if idx == -1:
            continue
        start = max(0, idx - 20)
        end = min(len(text), idx + len(phrase) + 20)
        flags.append(
            {
                "severity": rule["severity"],
                "rule": rule["rule"],
                "excerpt": text[start:end].strip(),
            }
        )
    return flags
