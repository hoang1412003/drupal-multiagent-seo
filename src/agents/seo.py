from ai_core import call_agent

SYSTEM_PROMPT = (
    "Bạn là chuyên gia SEO. Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả "
    "hay văn phong:\n"
    "1. Từ khóa chính (rút ra từ tiêu đề) có xuất hiện tự nhiên trong nội dung không, "
    "đặc biệt trong 100 từ đầu.\n"
    "2. Tiêu đề có trong khoảng 50-60 ký tự không (chuẩn hiển thị trên Google).\n"
    "3. Nội dung có cấu trúc heading rõ ràng không (thẻ <h2>/<h3> nếu có trong HTML).\n"
    "4. Độ dài nội dung có đủ cho SEO không (khuyến nghị tối thiểu khoảng 300 từ)."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "keyword_analysis": {
            "type": "object",
            "properties": {
                "main_keyword": {"type": "string"},
                "found_in_title": {"type": "boolean"},
                "density_ok": {"type": "boolean"},
            },
            "required": ["main_keyword", "found_in_title", "density_ok"],
            "additionalProperties": False,
        },
        "meta_issues": {"type": "array", "items": {"type": "string"}},
        "heading_structure_ok": {"type": "boolean"},
    },
    "required": ["score", "keyword_analysis", "meta_issues", "heading_structure_ok"],
    "additionalProperties": False,
}


def run(title: str, body: str) -> dict:
    return call_agent(SYSTEM_PROMPT, title, body, OUTPUT_SCHEMA)
