"""Test vong doi soat (spec 2026-08-07 muc 6.3 va 6.3.1).

Tiem het phu thuoc -> khong can Postgres, khong can Drupal.
Chay: .venv\\Scripts\\python.exe scripts\\test_reconcile.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import reconcile


def _gom(status="queued"):
    """`status` mo phong ket qua q.enqueue() thuc: "queued" (job moi tao) la
    mac dinh vi da phan lon test o day dang kiem "co enqueue hay khong", chu
    khong kiem gia tri tra ve cua enqueue_fn."""
    da_xep = []
    return da_xep, lambda conn, node_id, content_hash, source: (
        da_xep.append((node_id, content_hash, source))
        or {"status": status, "job_id": 1})


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


def test_enqueue_tra_khac_queued_thi_khong_dem_them():
    """Sua loi: `enqueue_fn(...)` truoc day bi bo gia tri tra ve, `da_xep += 1`
    tang VO DIEU KIEN moi lan goi - worker in "doi soat them 1 job" ke ca khi
    khong co job nao duoc tao that (VD duong event da xep hang cap nay truoc
    do, enqueue_fn tra 'duplicate', khong INSERT gi ca)."""
    da_xep, fn = _gom(status="duplicate")
    n = reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u5", "content_hash": "moi",
                          "hash_da_cham": "cu"}],
        enqueue_fn=fn, co_that_bai=lambda c, n_, h: False)
    assert len(da_xep) == 1, "enqueue_fn phai duoc goi"
    assert n == 0, f"enqueue_fn tra 'duplicate' -> khong duoc dem la da xep them: {n}"
    print("[PASS] enqueue_fn tra 'duplicate' -> khong dem them job")


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


def test_mot_node_hong_khong_giet_ca_luot():
    """Spec muc 9: mot node hong KHONG duoc giet toan bo luot doi soat.

    Neu mot phan tu cua liet_ke() thieu khoa (VD content_hash) -> KeyError.
    Nhung nhung node con lai PHAI van duoc xu ly - khong duoc bo qua.
    """
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [
            {"node_id": "hong", "hash_da_cham": None},  # Thieu content_hash
            {"node_id": "tot", "content_hash": "moi", "hash_da_cham": "cu"},  # Hop le
        ],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    # Phan tu "tot" van phai duoc xep, khong bi lung tung vi phan tu truoc no hong
    assert da_xep == [("tot", "moi", "reconcile")], f"node tot bi lung tung: {da_xep}"
    print("[PASS] mot node hong khong giet toan bo luot (node tot van duoc xep)")


def test_liet_ke_loi_thi_nem_ra_ngoai():
    """Spec muc 9: neu liet_ke() loi -> de loi vang ra, khong tu nuot.

    liet_ke() hong = nguon du lieu hong (Drupal chet, mang loi). Day la loi
    nguon - worker.py co try/except bao quanh reconcile.quet() de ghi log
    dung chung. Neu quet() tu nuot loi thi tao tac them mot tang nuot loi,
    va khi do khong ai biet doi soat da ngung hoat dong.
    """
    da_xep, fn = _gom()

    def liet_ke_loi():
        raise ValueError("Drupal JSON:API loi")

    try:
        reconcile.quet(
            None,
            liet_ke=liet_ke_loi,
            enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
        assert False, "quet() phai de loi vang ra, khong tu nuot"
    except ValueError as e:
        assert str(e) == "Drupal JSON:API loi", e
        print("[PASS] liet_ke() loi thi quet() de loi vang ra (khong nuot)")


if __name__ == "__main__":
    failed = False
    for fn_ in (
        test_hash_khop_thi_khong_xep,
        test_hash_khac_thi_xep,
        test_chua_cham_bao_gio_thi_xep,
        test_KHONG_hoi_sinh_job_da_dead_letter,
        test_enqueue_tra_khac_queued_thi_khong_dem_them,
        test_tra_ve_so_job_da_xep,
        test_mot_node_hong_khong_giet_ca_luot,
        test_liet_ke_loi_thi_nem_ra_ngoai,
    ):
        try:
            fn_()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn_.__name__}: {e}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
