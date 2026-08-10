"""Test thủ công cho phần rule-based (blacklist) của Compliance Agent —
không gọi LLM, chỉ kiểm tra match_blacklist() có bắt đúng cụm từ cấm không.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_compliance_rules.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import _cp1_claim_tuyet_doi, match_blacklist

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

# Mức CP1: 0 = critical -> veto, 1 = low -> KHÔNG veto, 2 = sạch.
#
# Cụm `can_pham_vi` chỉ lên mức 0 khi quanh đó có phạm vi so sánh. Đo trên 33
# mẫu gold set: cách cũ (mọi lần khớp -> mức 0) cho 14 bài bị veto mà chỉ 3
# bài vi phạm thật, precision 0,21. Xem docstring `_cp1_claim_tuyet_doi`.
CP1_CASES = [
    # --- mức 0: có phạm vi so sánh -> vẫn phải veto ---
    ("VF3 tốt nhất thị trường Việt Nam", 0, "claim + phạm vi"),
    ("Đây là sản phẩm duy nhất trên thị trường có tính năng này", 0, "claim + phạm vi"),
    ("Mẫu xe an toàn nhất phân khúc SUV điện", 0, "claim + phạm vi"),
    ("VF9 đi xa nhất phân khúc", 0, "claim + phạm vi"),

    # --- mức 0 dù KHÔNG có phạm vi: cam kết tuyệt đối, tự thân đã vi phạm ---
    ("VinFast cam kết 100% chất lượng cho mọi xe", 0, "cam kết tuyệt đối"),
    ("Xe đảm bảo an toàn tuyệt đối cho người dùng", 0, "cam kết tuyệt đối"),
    ("Dòng xe này không đối thủ về khả năng vận hành", 0, "cam kết tuyệt đối"),

    # --- mức 1: dùng trạng ngữ/lượng từ, KHÔNG được veto (đây là phần sửa) ---
    ("Đây là cách tốt nhất để bảo quản pin xe điện", 1, "trạng ngữ"),
    ("Giữ xe ở trạng thái tốt nhất bằng cách sạc đúng cách", 1, "trạng ngữ"),
    ("Gói thuê pin chỉ áp dụng duy nhất 01 gói cố định", 1, "lượng từ"),
    ("Bảng thông số: Thời gian sạc nhanh nhất. Quãng đường sau 1 lần sạc", 1, "tiêu đề bảng"),

    # --- mức 2: không khớp cụm nào ---
    ("VF5 có quãng đường 326km theo chuẩn NEDC", 2, "sạch"),
    ("Đây là mẫu số 10 trong catalogue", 2, "sạch - không khớp 'số 1'"),

    # --- ca xấu nhất đã biết: claim thật nhưng không nêu phạm vi -> mức 1.
    # KHÔNG biến mất, vẫn sinh flag `low` cho người duyệt thấy. Test này khoá
    # lại đánh đổi đó để nó không âm thầm đổi mà không ai biết.
    ("VinFast là thương hiệu xe điện tốt nhất.", 1, "ĐÁNH ĐỔI: claim thiếu phạm vi"),
]


def _kiem_cp1() -> bool:
    hong = False
    print("\n--- Mức CP1 (0 = veto, 1 = low, 2 = sạch) ---")
    for text, mong, ghi_chu in CP1_CASES:
        muc = _cp1_claim_tuyet_doi({"body": text})["level"]
        ok = muc == mong
        hong = hong or not ok
        print(f"[{'PASS' if ok else 'FAIL'}] muc {muc} (ky vong {mong}) "
              f"| {ghi_chu:<28} | '{text[:52]}'")
    return hong


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
    failed = _kiem_cp1() or failed
    sys.exit(1 if failed else 0)
