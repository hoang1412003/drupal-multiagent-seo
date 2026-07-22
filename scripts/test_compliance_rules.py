"""Test thủ công cho phần rule-based (blacklist) của Compliance Agent —
không gọi LLM, chỉ kiểm tra match_blacklist() có bắt đúng cụm từ cấm không.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_compliance_rules.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import match_blacklist

CASES = [
    ("VF3 tốt nhất thị trường Việt Nam", 1),
    ("VinFast VF3 là lựa chọn tuyệt vời cho gia đình bạn", 0),
    ("Đây là chiếc xe SỐ 1 hiện nay", 1),
    ("Chương trình giảm giá không giới hạn tới hết tháng", 1),
    ("VF3 tốt nhất và số 1 thị trường", 2),
]

if __name__ == "__main__":
    failed = False
    for text, expected_count in CASES:
        flags = match_blacklist(text)
        status = "PASS" if len(flags) == expected_count else "FAIL"
        if status == "FAIL":
            failed = True
        print(f"[{status}] '{text}' -> {len(flags)} flag(s) (ky vong {expected_count})")
        for f in flags:
            print(f"    {f}")
    sys.exit(1 if failed else 0)
