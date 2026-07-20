from ai_core import call_agent

SYSTEM_PROMPT = (
    "Bạn là biên tập viên nội dung marketing. Chỉ đánh giá chính tả, ngữ pháp, "
    "văn phong, độ rõ ràng, câu quá dài/tối nghĩa, tính mạch lạc. "
    "KHÔNG đánh giá SEO hay thương hiệu."
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
                    "type": {"type": "string"},
                    "location": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["type", "location", "suggestion"],
                "additionalProperties": False,
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "issues", "strengths"],
    "additionalProperties": False,
}


def run(title: str, body: str) -> dict:
    return call_agent(SYSTEM_PROMPT, title, body, OUTPUT_SCHEMA)
