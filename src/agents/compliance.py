import json
import os

from ai_core import call_agent

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


SYSTEM_PROMPT = (
    "Bạn là chuyên gia kiểm duyệt tuân thủ pháp lý cho nội dung marketing. "
    "Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả, văn phong hay SEO:\n"
    "1. Claim nhạy cảm/thổi phồng thiếu căn cứ (ví dụ: cam kết hiệu quả tuyệt "
    "đối, so sánh hơn hẳn đối thủ không có bằng chứng).\n"
    "2. Nội dung có nguy cơ vi phạm luật quảng cáo Việt Nam.\n"
    "3. Thông tin giá/khuyến mãi gây hiểu nhầm (ví dụ thời hạn không rõ ràng, "
    "điều kiện áp dụng bị giấu).\n"
    "Với mỗi vi phạm tìm thấy, tạo 1 flag với severity 'low' (nhẹ), 'medium' "
    "(đáng chú ý), hoặc 'critical' (nghiêm trọng, rủi ro pháp lý rõ ràng).\n"
    "Luôn trả lời bằng tiếng Việt trong tất cả các trường văn bản."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "critical"]},
                    "rule": {"type": "string"},
                    "excerpt": {"type": "string"},
                },
                "required": ["severity", "rule", "excerpt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["score", "flags"],
    "additionalProperties": False,
}


def run(title: str, body: str) -> dict:
    llm_result = call_agent(SYSTEM_PROMPT, title, body, OUTPUT_SCHEMA)
    rule_flags = match_blacklist(f"{title}\n{body}")
    return {
        "score": llm_result["score"],
        "flags": llm_result["flags"] + rule_flags,
    }
