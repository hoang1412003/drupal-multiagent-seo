from ai_core import call_agent
from prompt_builder import boc_noi_dung

_FIELDS = ("title", "body", "summary")

SYSTEM_PROMPT = (
    "Bạn là biên tập viên nội dung marketing. Chỉ đánh giá chính tả, ngữ pháp, "
    "văn phong, độ rõ ràng, câu quá dài/tối nghĩa, tính mạch lạc. "
    "KHÔNG đánh giá SEO hay thương hiệu.\n"
    "Nội dung gồm nhiều trường (field) nằm trong các thẻ <title>, <body>, "
    "<summary>. Với MỖI lỗi tìm thấy, ghi rõ nó thuộc field nào vào trường "
    "'field' (một trong: title, body, summary).\n"
    "Luôn trả lời bằng tiếng Việt trong tất cả các trường văn bản."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": ["title", "body", "summary"]},
                    "type": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["field", "type", "suggestion"],
                "additionalProperties": False,
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "issues", "strengths"],
    "additionalProperties": False,
}


def run(fields: dict) -> dict:
    # M1 + M3 (docs/prompt-injection.md mục 5). Agent này KHÔNG dùng phần
    # `doan_an` trả về: nó chấm chính tả/văn phong, không có thẩm quyền kết
    # luận về chỉ dẫn ẩn - đó là việc của Compliance.
    content, _ = boc_noi_dung(fields, _FIELDS)
    return call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)
