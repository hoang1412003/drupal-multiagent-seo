"""Test logic fact_check (CP3) bang fake extract/compare/retriever - khong
goi LLM hay KB that.

Bon nhanh, va viec PHAN BIET DUOC chung la ly do danh_gia() thay cho ban cu
tra list flag: ban cu tra [] cho ca ba truong hop "khong co claim", "khong
tra duoc" va "moi so lieu khop" - ba tinh huong phai ra ba muc khac nhau.

  - so lieu lech (cung model) -> muc 0
  - khong tra duoc (retrieve rong) -> muc 1, KHONG phai 0
  - thong so tra ve khac model -> compare tra 'unverifiable' -> muc 1
  - khong co claim nao -> NA

Chay: .venv\\Scripts\\python.exe scripts\\test_fact_check.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import fact_check

CLAIM_VF8 = {"model": "VF 8", "metric": "tam_hoat_dong", "value": "500km",
             "field": "body", "excerpt": "VF 8 chạy 500km"}


def test_mismatch_ra_muc_0():
    kq = fact_check.danh_gia(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 8: 420km", "model": "VF 8", "score": 0.9, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "mismatch", "reason": "500 != 420"}],
    )
    assert kq["level"] == 0, kq
    assert kq["occurrences"][0]["field"] == "body"
    assert "sai lệch" in kq["occurrences"][0]["rule"].lower()
    print("[PASS] so lieu lech -> muc 0")


def test_khong_tra_duoc_ra_muc_1():
    """Nguyen tac an toan quan trong nhat cua CP3 (rubrics.md muc 6.2): KB chi
    co thong so mot so model, 'khong tra duoc' != 'sai'. Ra muc 0 o day se tu
    choi oan moi bai nhac model ngoai KB."""
    kq = fact_check.danh_gia(
        {"body": "Model XYZ chạy 999km"},
        extract_fn=lambda f: [{"model": "XYZ", "metric": "tam_hoat_dong",
                               "value": "999km", "field": "body", "excerpt": "XYZ 999km"}],
        retriever=lambda q, ct, lc, **k: [],  # khong tra duoc
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc goi compare khi khong co hit")),
    )
    assert kq["level"] == 1, f"phai la muc 1 (khong kiem chung duoc), got {kq}"
    assert "chưa kiểm chứng" in kq["occurrences"][0]["rule"].lower(), kq["occurrences"]
    print("[PASS] khong tra duoc -> muc 1, nhan rieng (khong bao la sai)")


def test_unverifiable_ra_muc_1():
    kq = fact_check.danh_gia(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 9: 438km", "model": "VF 9", "score": 0.6, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "unverifiable", "reason": "thong so la VF 9, khong phai VF 8"}],
    )
    assert kq["level"] == 1, f"khac model -> unverifiable -> muc 1, got {kq}"
    print("[PASS] khac model -> unverifiable -> muc 1")


def test_match_ra_muc_2():
    kq = fact_check.danh_gia(
        {"body": "VF 8 chạy 420km"},
        extract_fn=lambda f: [dict(CLAIM_VF8, value="420km")],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 8: 420km", "model": "VF 8", "score": 0.9, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "match", "reason": "khop"}],
    )
    assert kq["level"] == 2, kq
    assert kq["occurrences"] == []
    print("[PASS] moi claim khop -> muc 2")


def test_khong_co_claim_ra_na():
    """NA, khong phai muc 2: bai khong co so lieu nao thi khong co gi de doi
    chieu - cho muc 2 la cong diem mien phi cho moi bai khong co con so."""
    kq = fact_check.danh_gia(
        {"body": "bài không có số liệu"},
        extract_fn=lambda f: [],
        retriever=lambda *a, **k: (_ for _ in ()).throw(AssertionError("khong duoc retrieve khi khong co claim")),
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc compare")),
    )
    assert kq["level"] is None, f"khong co claim -> NA, got {kq}"
    print("[PASS] khong co claim -> NA, dung som")


def test_mot_claim_khop_mot_claim_khong_tra_duoc_ra_muc_1():
    """Muc 2 chi danh cho bai MOI claim deu tra duoc va khop. Con mot claim
    chua ket luan duoc thi van la 'dat mot phan'."""
    claim_khac = {"model": "XYZ", "metric": "pin", "value": "99kWh",
                  "field": "body", "excerpt": "XYZ pin 99kWh"}
    kq = fact_check.danh_gia(
        {"body": "VF 8 chạy 420km. XYZ pin 99kWh"},
        extract_fn=lambda f: [dict(CLAIM_VF8, value="420km"), claim_khac],
        retriever=lambda q, ct, lc, **k: (
            [{"text": "VF 8: 420km", "model": "VF 8", "score": 0.9, "source_url": "u"}]
            if "VF 8" in q else []
        ),
        compare_fn=lambda pairs: [{"index": 0, "verdict": "match", "reason": "khop"}],
    )
    assert kq["level"] == 1, f"con claim chua ket luan -> muc 1, got {kq}"
    assert len(kq["occurrences"]) == 1, kq["occurrences"]
    print("[PASS] mot claim chua tra duoc -> muc 1 (khong len muc 2)")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_mismatch_ra_muc_0,
        test_khong_tra_duoc_ra_muc_1,
        test_unverifiable_ra_muc_1,
        test_match_ra_muc_2,
        test_khong_co_claim_ra_na,
        test_mot_claim_khop_mot_claim_khong_tra_duoc_ra_muc_1,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
