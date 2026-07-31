import json
import os
import re

from ai_core import call_agent
from agents import fact_check

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

    Mỗi cụm khớp tạo 1 flag. Severity lấy từ rule entry trong JSON
    (hiện tất cả đều là "critical"). Chỉ bắt lần khớp đầu tiên của mỗi
    cụm trong text (không đếm các lần lặp lại).

    Dùng \\b (word boundary) thay vì so khớp chuỗi con thô, để tránh khớp
    nhầm vào số dài hơn (VD cụm "số 1" khớp nhầm vào "số 10", "số 100").
    """
    flags = []
    for rule in _load_rules():
        pattern = r"\b" + re.escape(rule["text"]) + r"\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 20)
        flags.append(
            {
                "severity": rule["severity"],
                "rule": rule["rule"],
                "excerpt": text[start:end].strip(),
            }
        )
    return flags


SYSTEM_PROMPT = (
    "Bạn là chuyên gia kiểm duyệt tuân thủ pháp lý cho nội dung marketing xe điện "
    "(ô tô điện, xe máy điện). "
    "Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả, văn phong hay SEO:\n"
    "1. Claim nhạy cảm/thổi phồng thiếu căn cứ (ví dụ: cam kết hiệu quả tuyệt "
    "đối, so sánh hơn hẳn đối thủ không có bằng chứng).\n"
    "2. Nội dung có nguy cơ vi phạm luật quảng cáo Việt Nam.\n"
    "3. Thông tin giá/khuyến mãi gây hiểu nhầm (ví dụ thời hạn không rõ ràng, "
    "điều kiện áp dụng bị giấu).\n"
    "4. Claim tầm hoạt động/quãng đường (ví dụ 'đi được 420km một lần sạc') mà "
    "KHÔNG nêu điều kiện đo (NEDC/WLTP) hoặc lưu ý thực tế có thể khác - đây là "
    "thông tin dễ gây hiểu nhầm cho người mua.\n"
    "5. Claim thời gian sạc (ví dụ 'sạc đầy 30 phút') mà KHÔNG nêu loại trụ sạc "
    "hoặc dải phần trăm (ví dụ 10-70%).\n"
    "6. So sánh trực tiếp với đối thủ cụ thể (Tesla, BYD, Toyota...) theo hướng "
    "hơn hẳn - có nguy cơ vi phạm Luật Cạnh tranh 2018 về so sánh trực tiếp.\n"
    "7. Điều khoản thuê pin/chính sách pin nêu thiếu điều kiện, phí hoặc thời hạn.\n"
    "Với mỗi vi phạm tìm thấy, tạo 1 flag với severity 'low' (nhẹ), 'medium' "
    "(đáng chú ý), hoặc 'critical' (nghiêm trọng, rủi ro pháp lý rõ ràng).\n"
    "Nội dung gồm nhiều trường được đánh dấu bằng nhãn [title], [body], "
    "[meta_description]. Với MỖI flag, ghi rõ vi phạm thuộc field nào vào "
    "trường 'field' (một trong: title, body, meta_description).\n"
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
                    "field": {
                        "type": "string",
                        "enum": ["title", "body", "meta_description"],
                    },
                    "severity": {"type": "string", "enum": ["low", "medium", "critical"]},
                    "rule": {"type": "string"},
                    "excerpt": {"type": "string"},
                },
                "required": ["field", "severity", "rule", "excerpt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["score", "flags"],
    "additionalProperties": False,
}

# Các field rule-based blacklist quét (chỉ field chứa văn bản marketing tự do)
_RULE_FIELDS = ("title", "body", "meta_description")


def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi") -> dict:
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}"
    )
    llm_result = call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)

    # Rule-based: quét từng field riêng để gắn đúng field vào flag
    rule_flags = []
    for field_name in _RULE_FIELDS:
        for flag in match_blacklist(fields.get(field_name, "")):
            flag["field"] = field_name
            rule_flags.append(flag)

    # Nguồn thứ 3: RAG fact-check (CP3). Bọc try/except vì KB có thể chưa
    # dựng (chạy src/kb/build_kb.py) - khi đó fact-check bỏ qua, KHÔNG làm
    # sập cả Compliance Agent.
    try:
        fact_check_flags = fact_check.run(fields, content_type=content_type, langcode=langcode)
    except Exception:
        fact_check_flags = []

    return {
        "score": llm_result["score"],
        "flags": llm_result["flags"] + rule_flags + fact_check_flags,
    }
