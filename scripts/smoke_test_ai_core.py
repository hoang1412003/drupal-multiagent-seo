"""Test thủ công cho src/ai_core.py — tự chạy để xác nhận việc gọi Claude API
hoạt động end-to-end với ANTHROPIC_API_KEY của bạn.

Cách chạy (từ thư mục gốc project, sau khi activate .venv và điền .env):
    .venv\\Scripts\\python.exe scripts\\smoke_test_ai_core.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_core import call_agent

system_prompt = (
    "Bạn là biên tập viên nội dung marketing. Chỉ đánh giá chính tả, ngữ pháp, "
    "văn phong, độ rõ ràng, câu quá dài/tối nghĩa, tính mạch lạc. "
    "KHÔNG đánh giá SEO hay thương hiệu."
)

title = "Khuyến mãi VinFast VF3 tháng 7 - Giảm giá đến 50 triệu"
body = (
    "VinFast chính thức triển khai chương trình ưu đãi đặc biệt dành cho khách hàng "
    "mua xe VF3 trong tháng 7. Khách hàng sẽ được giảm giá lên đến 50 triệu đồng, "
    "tặng kèm gói bảo hiểm 1 năm và miễn phí sạc pin tại các trạm VinFast trên toàn quốc. "
    "Chương trình áp dụng từ ngày 17/07/2026 đến hết ngày 31/07/2026, số lượng có hạn."
)

output_schema = {
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

if __name__ == "__main__":
    result = call_agent(system_prompt, title, body, output_schema)
    print(json.dumps(result, ensure_ascii=False, indent=2))
