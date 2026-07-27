from ai_core import call_agent

SYSTEM_PROMPT = (
    "Bạn là chuyên gia SEO. Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả "
    "hay văn phong. Nội dung gồm nhiều trường được đánh dấu bằng nhãn [title], "
    "[meta_description], [url_alias], [body], [image_alt]:\n"
    "1. [title] dài khoảng 50-60 ký tự, chứa từ khóa chính.\n"
    "2. [meta_description] có tồn tại không, dài khoảng 150-160 ký tự, chứa từ "
    "khóa. Nếu để trống -> đây là lỗi.\n"
    "3. [url_alias] (slug) ngắn gọn, chứa từ khóa, không dấu, dùng gạch nối. "
    "Nếu để trống -> đây là lỗi.\n"
    "4. Từ khóa chính (rút ra từ tiêu đề) xuất hiện tự nhiên trong [body], đặc "
    "biệt 100 từ đầu; nội dung đủ dài cho SEO (tối thiểu ~300 từ); có cấu trúc "
    "heading <h2>/<h3>.\n"
    "5. [image_alt] có tồn tại và mô tả đúng ảnh không. Nếu để trống -> lỗi.\n"
    "Với MỖI lỗi, ghi rõ nó thuộc field nào vào trường 'field' (một trong: "
    "title, meta_description, url_alias, body, image_alt).\n"
    "Luôn trả lời bằng tiếng Việt trong tất cả các trường văn bản."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "main_keyword": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": ["title", "meta_description", "url_alias", "body", "image_alt"],
                    },
                    "type": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["field", "type", "suggestion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["score", "main_keyword", "issues"],
    "additionalProperties": False,
}


def run(fields: dict) -> dict:
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}\n\n"
        f"[url_alias] {fields.get('url_alias', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[image_alt] {fields.get('image_alt', '')}"
    )
    return call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)
