"""Test thủ công (offline, không gọi LLM/Drupal) cho cách xử lý khi một agent
không trả được kết quả - docs/architecture.md mục 6.4.

Kiểm 2 điều tài liệu yêu cầu mà code từng thiếu:

1. Agent lỗi KHÔNG bị quy thành 0 điểm khi ghi về Drupal (spec mục 5.1:
   "Agent lỗi không bị cho điểm 0" - ghi 0 khiến người duyệt hiểu nhầm bài
   cực tệ, trong khi thực tế là chưa đánh giá được).
2. Báo cáo có ghi chú bằng chữ (report["note"]) nêu rõ vì sao điểm chưa đầy
   đủ / vì sao phải review thủ công.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_missing_agent_report.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import graph
from graph import aggregator_node

failed = False


def check(label, cond):
    global failed
    status = "PASS" if cond else "FAIL"
    if not cond:
        failed = True
    print(f"[{status}] {label}")


# --- 1. Compliance lỗi -> needs_revision, không có điểm, có note -----------
state_no_compliance = {
    "node_id": "n-compliance-loi",
    "content_quality_result": {"score": 95},
    "seo_result": {"score": 95},
    "brand_result": {"score": 95},
    "compliance_result": None,
}
out = aggregator_node(state_no_compliance)
report = out["report"]

check("Compliance lỗi -> decision = needs_revision (không bao giờ tự publish)",
      report["decision"] == "needs_revision")
check("Compliance lỗi -> final_score = None (chưa đánh giá được, KHÔNG phải 0)",
      report["final_score"] is None)
check("Compliance lỗi -> missing_agents liệt kê compliance",
      report["missing_agents"] == ["compliance"])
check("Compliance lỗi -> report có note giải thích cần review thủ công",
      "compliance" in report.get("note", "").lower())


# --- 2. Một agent thường lỗi -> chia lại trọng số + có note ----------------
state_no_seo = {
    "node_id": "n-seo-loi",
    "content_quality_result": {"score": 80},
    "seo_result": None,
    "brand_result": {"score": 80},
    "compliance_result": {"score": 80, "flags": []},
}
out2 = aggregator_node(state_no_seo)
report2 = out2["report"]

# 3 agent còn lại đều 80 -> điểm chia lại theo tổng trọng số 0.80 vẫn = 80
check("SEO lỗi -> điểm chia lại theo trọng số còn lại (80)",
      report2["final_score"] == 80)
check("SEO lỗi -> decision = publish (điểm >= 80)",
      report2["decision"] == "publish")
check("SEO lỗi -> report có note nêu rõ điểm chưa đầy đủ",
      "SEO" in report2.get("note", ""))


# --- 3. write_back nhận đúng score None, note hiện trong gợi ý ------------
captured = {}


def _fake_write_back(node_id, status, score, suggestions, report_json=None):
    captured["score"] = score
    captured["suggestions"] = suggestions
    captured["report_json"] = report_json


graph.write_back = _fake_write_back  # chặn gọi Drupal thật

graph.write_back_node({
    "node_id": "n-compliance-loi",
    "decision": report["decision"],
    "final_score": report["final_score"],
    "report": report,
})

check("write_back nhận score = None khi chưa chấm được (KHÔNG bị ép thành 0)",
      captured["score"] is None)
check("note xuất hiện trong nội dung gợi ý ghi về Drupal",
      "LƯU Ý" in captured["suggestions"])

print("\n--- Gợi ý ghi về Drupal (trường hợp Compliance lỗi) ---")
print(captured["suggestions"])
print("-------------------------------------------------------\n")


# --- 4. Điểm 0.0 hợp lệ vẫn phải được ghi nguyên vẹn -----------------------
graph.write_back_node({
    "node_id": "n-diem-0",
    "decision": "rejected",
    "final_score": 0.0,
    "report": {"details": {}},
})
check("điểm 0.0 thật (bài quá tệ) vẫn ghi 0.0, không nhầm thành None",
      captured["score"] == 0.0)

# --- 5. Nguyên tắc None != 0 phải đúng ở CẢ báo cáo JSON -------------------
# Module vf_ai_review đọc JSON chứ không đọc field điểm, nên nếu JSON quy
# None thành 0 thì giao diện vẫn hiển thị sai dù field điểm đúng.
check("báo cáo JSON của bài điểm 0.0 ghi 0.0",
      captured["report_json"]["final_score"] == 0.0)

graph.write_back_node({
    "node_id": "n-compliance-loi",
    "decision": report["decision"],
    "final_score": report["final_score"],
    "report": report,
})
check("báo cáo JSON khi Compliance lỗi ghi final_score = None",
      captured["report_json"]["final_score"] is None)

sys.exit(1 if failed else 0)
