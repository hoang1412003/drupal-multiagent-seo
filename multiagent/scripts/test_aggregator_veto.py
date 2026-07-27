"""Test thủ công cho logic veto_reason trong aggregator_node (src/graph.py) —
gọi thẳng aggregator_node() với state giả (không gọi LLM/Drupal), xác nhận
veto_reason chỉ xuất hiện khi Compliance veto qua flag critical (không phải
do điểm thấp).

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_aggregator_veto.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import aggregator_node

CRITICAL_FLAG = {
    "severity": "critical",
    "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)",
    "excerpt": "...tốt nhất...",
}

CASES = [
    (
        "Compliance score cao (85) nhung co flag critical -> rejected + co veto_reason",
        {
            "node_id": "test-1",
            "content_quality_result": {"score": 90},
            "seo_result": {"score": 90},
            "brand_result": {"score": 90},
            "compliance_result": {"score": 85, "flags": [CRITICAL_FLAG]},
        },
        "rejected",
        True,
    ),
    (
        "Compliance score thap (40) va co flag critical -> rejected nhung KHONG co veto_reason (score da tu giai thich)",
        {
            "node_id": "test-2",
            "content_quality_result": {"score": 90},
            "seo_result": {"score": 90},
            "brand_result": {"score": 90},
            "compliance_result": {"score": 40, "flags": [CRITICAL_FLAG]},
        },
        "rejected",
        False,
    ),
    (
        "Compliance sach (khong flag), score cao -> publish, khong co veto_reason",
        {
            "node_id": "test-3",
            "content_quality_result": {"score": 90},
            "seo_result": {"score": 90},
            "brand_result": {"score": 90},
            "compliance_result": {"score": 90, "flags": []},
        },
        "publish",
        False,
    ),
]

if __name__ == "__main__":
    failed = False
    for label, state, expected_decision, expect_veto_reason in CASES:
        result = aggregator_node(state)
        report = result["report"]
        decision_ok = report["decision"] == expected_decision
        veto_ok = ("veto_reason" in report) == expect_veto_reason
        status = "PASS" if (decision_ok and veto_ok) else "FAIL"
        if status == "FAIL":
            failed = True
        print(
            f"[{status}] {label}\n"
            f"    decision={report['decision']} (ky vong {expected_decision}), "
            f"veto_reason={'co' if 'veto_reason' in report else 'khong'} "
            f"(ky vong {'co' if expect_veto_reason else 'khong'})"
        )
    sys.exit(1 if failed else 0)
