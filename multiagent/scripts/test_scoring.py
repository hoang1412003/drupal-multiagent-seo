"""Test ham tinh diem tat dinh (docs/rubrics.md muc 2.2).

Cap doi chung quan trong nhat: NA phai bi loai khoi MAU SO, khong duoc quy
thanh 0 - neu quy thanh 0 thi moi bai khong nhac toi tieu chi do deu bi tru
diem oan.
Chay: .venv\\Scripts\\python.exe scripts\\test_scoring.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scoring import score_from_criteria


def _c(*levels):
    return [{"id": f"BV{i + 1}", "level": lv} for i, lv in enumerate(levels)]


def test_vi_du_trong_spec():
    # BV1=0, BV2=2, BV3=1, BV4=2, BV5=2, BV6=2, BV7=2 -> tong 11 / 14
    assert score_from_criteria(_c(0, 2, 1, 2, 2, 2, 2)) == 78.6
    print("[PASS] vi du spec muc 5.5 -> 78.6")


def test_tat_dinh_100_lan():
    criteria = _c(0, 2, 1, 2, 2, 2, 2)
    ket_qua = {score_from_criteria(criteria) for _ in range(100)}
    assert ket_qua == {78.6}, ket_qua
    print("[PASS] chay 100 lan ra dung mot so")


def test_na_bi_loai_khoi_mau_so():
    # 6 tieu chi muc 2 + 1 NA -> 12/12 = 100
    assert score_from_criteria(_c(2, 2, 2, 2, 2, 2, None)) == 100.0
    print("[PASS] NA bi loai khoi mau so -> 100.0")


def test_muc_0_khac_han_na():
    # 6 tieu chi muc 2 + 1 muc 0 -> 12/14 = 85.7
    assert score_from_criteria(_c(2, 2, 2, 2, 2, 2, 0)) == 85.7
    print("[PASS] muc 0 -> 85.7, khac han NA -> 100.0")


def test_tat_ca_na_tra_none():
    assert score_from_criteria(_c(None, None, None)) is None
    print("[PASS] tat ca NA -> None (chua cham duoc, khong phai 0 diem)")


def test_criteria_rong_tra_none():
    assert score_from_criteria([]) is None
    print("[PASS] khong co tieu chi nao -> None")


def test_tat_ca_dat():
    assert score_from_criteria(_c(2, 2, 2)) == 100.0
    print("[PASS] tat ca dat -> 100.0")


def test_tat_ca_khong_dat():
    assert score_from_criteria(_c(0, 0, 0)) == 0.0
    print("[PASS] tat ca khong dat -> 0.0")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_vi_du_trong_spec,
        test_tat_dinh_100_lan,
        test_na_bi_loai_khoi_mau_so,
        test_muc_0_khac_han_na,
        test_tat_ca_na_tra_none,
        test_criteria_rong_tra_none,
        test_tat_ca_dat,
        test_tat_ca_khong_dat,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
