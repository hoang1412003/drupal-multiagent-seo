from ai_core import call_agent

SYSTEM_PROMPT = (
    "Bạn là biên tập viên nội dung marketing. Chỉ đánh giá chính tả, ngữ pháp, "
    "văn phong, độ rõ ràng, câu quá dài/tối nghĩa, tính mạch lạc. "
    "KHÔNG đánh giá SEO hay thương hiệu.\n"
    "Nội dung gồm nhiều trường (field) được đánh dấu bằng nhãn [title], [body], "
    "[summary]. Với MỖI lỗi tìm thấy, ghi rõ nó thuộc field nào vào trường "
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
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[summary] {fields.get('summary', '')}"
    )
    return call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)
