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
    ("Đây là mẫu số 10 trong catalogue", 0),
    ("VF9 đi xa nhất phân khúc, sạc nhanh nhất Việt Nam", 2),
    ("VF5 có quãng đường 326km theo chuẩn NEDC", 0),
    # Cụm KẾT THÚC bằng ký tự không phải chữ/số ('%'). \b sau '%' đòi ngay sau
    # đó phải là chữ/số, mà thực tế sau '%' luôn là dấu cách hoặc dấu câu -
    # nên hai cụm này chưa từng bị bắt lần nào dù đều là severity critical.
    ("VinFast cam kết 100% chất lượng cho mọi xe", 1),
    ("Sản phẩm đạt hiệu quả 100%.", 1),
    ("Chính sách bảo hành cam kết 100%", 1),
    # Chiều ngược lại: không được nới lỏng thành so khớp chuỗi con thô.
    ("Đây là mẫu số 10 trong catalogue", 0),
    ("Pin còn 100% dung lượng sau 1000 chu kỳ", 0),
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
