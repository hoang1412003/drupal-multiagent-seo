from ai_core import call_agent
from prompt_builder import boc_noi_dung

_FIELDS = ("title", "meta_description", "url_alias", "body", "image_alt")

SYSTEM_PROMPT = (
    "Bạn là chuyên gia SEO. Chỉ đánh giá các yếu tố sau, KHÔNG đánh giá chính tả "
    "hay văn phong. Nội dung gồm nhiều trường nằm trong các thẻ <title>, "
    "<meta_description>, <url_alias>, <body>, <image_alt>:\n"
    "1. <title> dài khoảng 50-60 ký tự, chứa từ khóa chính.\n"
    "2. <meta_description> có tồn tại không, dài khoảng 150-160 ký tự, chứa từ "
    "khóa. Nếu để trống -> đây là lỗi.\n"
    "3. <url_alias> (slug) ngắn gọn, chứa từ khóa, không dấu, dùng gạch nối. "
    "Nếu để trống -> đây là lỗi.\n"
    "4. Từ khóa chính (rút ra từ tiêu đề) xuất hiện tự nhiên trong <body>, đặc "
    "biệt 100 từ đầu; nội dung đủ dài cho SEO (tối thiểu ~300 từ); có cấu trúc "
    "heading <h2>/<h3>.\n"
    "5. <image_alt> liệt kê alt text của MỌI ảnh trong bài, mỗi ảnh một dòng, "
    "alt nằm sau dấu hai chấm. Dòng nào TRỐNG sau dấu hai chấm nghĩa là ảnh đó "
    "THIẾU alt -> đây là lỗi, nêu rõ ảnh thứ mấy. Ảnh có alt nhưng chung chung "
    "('hình ảnh', 'anh1') cũng là lỗi. Nếu <image_alt> hoàn toàn trống thì bài "
    "không có ảnh nào -> KHÔNG phải lỗi, bỏ qua tiêu chí này.\n"
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
    # M1 + M3 (docs/prompt-injection.md mục 5). Không bóc phần ẩn khỏi
    # `image_alt`: chuỗi đó do drupal_client dựng sẵn theo dòng, không phải
    # HTML của người viết.
    content, _ = boc_noi_dung(fields, _FIELDS, boc_an_o=("body",))
    return call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)
