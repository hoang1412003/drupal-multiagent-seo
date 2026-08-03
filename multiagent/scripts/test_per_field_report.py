"""Test thủ công (offline, không gọi LLM/Drupal) cho 2 phần của tính năng
báo cáo theo từng field:

1. drupal_client._extract_image_alt() - lấy alt text ảnh từ JSON:API resource.
2. graph.write_back_node() - gom gợi ý sửa theo từng field.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_per_field_report.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import drupal_client
import graph

failed = False


def check(label, cond):
    global failed
    status = "PASS" if cond else "FAIL"
    if not cond:
        failed = True
    print(f"[{status}] {label}")


# --- 1. _extract_image_alt -------------------------------------------------
res_with_alt = {
    "relationships": {"field_image": {"data": {"meta": {"alt": "VF 8 màu trắng"}}}}
}
res_no_image = {"relationships": {}}
res_null_image = {"relationships": {"field_image": {"data": None}}}

check("alt text đọc đúng khi có ảnh",
      drupal_client._extract_image_alt(res_with_alt) == "VF 8 màu trắng")
check("không có ảnh -> alt rỗng",
      drupal_client._extract_image_alt(res_no_image) == "")
check("field_image null -> alt rỗng",
      drupal_client._extract_image_alt(res_null_image) == "")


# --- 2. write_back_node gom theo field -------------------------------------
captured = {}


def _fake_write_back(node_id, status, score, suggestions, report_json=None):
    captured["suggestions"] = suggestions
    captured["report_json"] = report_json


graph.write_back = _fake_write_back  # chặn gọi Drupal thật

state = {
    "node_id": "n1",
    "decision": "needs_revision",
    "final_score": 70.0,
    "report": {
        "details": {
            "content_quality": {
                "score": 80,
                "issues": [{"field": "body", "type": "chính tả", "suggestion": "sửa 'thág' -> 'tháng'"}],
            },
            "seo": {
                "score": 60,
                "issues": [
                    {"field": "meta_description", "type": "trống", "suggestion": "thêm meta description"},
                    {"field": "title", "type": "quá dài", "suggestion": "rút ngắn tiêu đề"},
                ],
            },
            "brand": {"score": 100, "issues": []},
            "compliance": {
                "score": 90,
                "flags": [{"field": "title", "severity": "critical", "rule": "Luật Quảng cáo", "excerpt": "tốt nhất"}],
            },
        }
    },
}

graph.write_back_node(state)
s = captured["suggestions"]
print("\n--- Báo cáo gom theo field ---")
print(s)
print("------------------------------\n")

check("có nhóm Meta description", "── Meta description ──" in s)
check("có nhóm Tiêu đề (title)", "── Tiêu đề (title) ──" in s)
check("có nhóm Nội dung (body)", "── Nội dung (body) ──" in s)
check("lỗi title của SEO và Compliance cùng nằm dưới nhóm title",
      s.index("── Tiêu đề (title) ──") < s.index("rút ngắn tiêu đề")
      and s.index("── Tiêu đề (title) ──") < s.index("Luật Quảng cáo"))
check("không in khóa 'field' thô trong dòng gợi ý", "field:" not in s)
check("meta_description đứng trước body (đúng FIELD_ORDER)",
      s.index("── Meta description ──") < s.index("── Nội dung (body) ──"))

# --- 3. Báo cáo JSON gom theo cùng bộ field như chuỗi text ----------------
# Hai đầu ra dựng từ cùng một `report` nên phải nhất quán; lệch nhau nghĩa là
# module UI và người đọc text thấy hai bức tranh khác nhau.
rj = captured["report_json"]
check("báo cáo JSON gom đúng các field như chuỗi text",
      set(rj["fields"]) == {"title", "meta_description", "body"}, )
check("mỗi mục trong JSON đều có đủ khóa agent/label/severity",
      all({"agent", "label", "message", "excerpt", "severity"} <= set(m)
          for ds in rj["fields"].values() for m in ds))

sys.exit(1 if failed else 0)
