"""Test vong doi soat (spec 2026-08-07 muc 6.3 va 6.3.1).

Tiem het phu thuoc -> khong can Postgres, khong can Drupal.
Chay: .venv\\Scripts\\python.exe scripts\\test_reconcile.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import reconcile


def _gom():
    da_xep = []
    return da_xep, lambda conn, node_id, content_hash, source: da_xep.append(
        (node_id, content_hash, source))


def test_hash_khop_thi_khong_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u1", "content_hash": "h1",
                          "hash_da_cham": "h1"}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert da_xep == [], da_xep
    print("[PASS] da cham dung noi dung nay -> khong xep lai")


def test_hash_khac_thi_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u2", "content_hash": "moi",
                          "hash_da_cham": "cu"}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert da_xep == [("u2", "moi", "reconcile")], da_xep
    print("[PASS] noi dung da doi -> xep job bu")


def test_chua_cham_bao_gio_thi_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u3", "content_hash": "h3",
                          "hash_da_cham": None}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert len(da_xep) == 1, da_xep
    print("[PASS] chua cham bao gio -> xep job")


def test_KHONG_hoi_sinh_job_da_dead_letter():
    """Phep kiem quan trong nhat cua file nay (spec muc 6.3.1).

    Index dedup CO Y loai `failed`. Neu doi soat khong hoi them cau nay thi
    no se xep lai mot bai luon that bai MOI 5 PHUT, moi job thu 3 lan, va co
    che dead-letter bi vo hieu hoan toan - thanh vong lap tieu tien API vo han.
    """
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u4", "content_hash": "h4",
                          "hash_da_cham": None}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: True)
    assert da_xep == [], f"da hoi sinh job dead-letter: {da_xep}"
    print("[PASS] job da dead-letter KHONG bi doi soat hoi sinh")


def test_tra_ve_so_job_da_xep():
    _, fn = _gom()
    n = reconcile.quet(
        None,
        liet_ke=lambda: [
            {"node_id": "a", "content_hash": "1", "hash_da_cham": None},
            {"node_id": "b", "content_hash": "2", "hash_da_cham": "2"},
            {"node_id": "c", "content_hash": "3", "hash_da_cham": "cu"},
        ],
        enqueue_fn=fn, co_that_bai=lambda c, n_, h: False)
    assert n == 2, n
    print("[PASS] tra ve dung so job da xep")


if __name__ == "__main__":
    failed = False
    for fn_ in (
        test_hash_khop_thi_khong_xep,
        test_hash_khac_thi_xep,
        test_chua_cham_bao_gio_thi_xep,
        test_KHONG_hoi_sinh_job_da_dead_letter,
        test_tra_ve_so_job_da_xep,
    ):
        try:
            fn_()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn_.__name__}: {e}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
