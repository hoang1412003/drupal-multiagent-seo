r"""Kiem tra `load_auth_config` chet ngay khi cau hinh khoa sai.

Chuyen tu `test_admin_routes.py` (2026-08-21) khi xoa admin Jinja2. Console
dung dung ham nay: `api.py` goi no trong lifespan, truoc khi nhan request dau
tien.

Vi sao phai chet ngay thay vi chay tiep: hai khoa nay bao ve CSRF va chong do
mat khau. Neu thieu ma he thong tu sinh mot khoa ngau nhien roi chay tiep, no
van "hoat dong" - nhung moi lan khoi dong lai la mot khoa khac, va khong ai
phat hien ra cho toi khi can dieu tra mot su co. Chet ngay luc khoi dong la
cach duy nhat de sai sot nay khong im lang.

Khong can Postgres.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_auth_config.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform.admin import dependencies


HOP_LE = {
    "ADMIN_CSRF_KEY": "c" * 32,
    "ADMIN_THROTTLE_KEY": "t" * 32,
    "ADMIN_COOKIE_SECURE": "true",
}


def test_cau_hinh_hop_le_thi_nap_duoc():
    loaded = dependencies.load_auth_config(HOP_LE)
    assert loaded.cookie_secure is True
    print("[PASS] cau hinh hop le nap duoc, cookie_secure doc dung")


def test_khoa_thieu_ngan_trung_va_bool_sai_deu_chet_ngay():
    truong_hop = (
        ({"ADMIN_CSRF_KEY": ""}, "ADMIN_CSRF_KEY", "khoa CSRF de trong"),
        ({"ADMIN_THROTTLE_KEY": "short"}, "ADMIN_THROTTLE_KEY", "khoa qua ngan"),
        # Hai khoa TRUNG NHAU la loi that su nguy: dung mot bi mat cho hai muc
        # dich khac nhau lam lo cai nay keo theo lo cai kia.
        ({"ADMIN_THROTTLE_KEY": "c" * 32}, "khác nhau", "hai khoa trung nhau"),
        ({"ADMIN_COOKIE_SECURE": "sometimes"}, "true hoặc false", "bool sai"),
    )
    for ghi_de, phan_thong_bao, ten in truong_hop:
        try:
            dependencies.load_auth_config({**HOP_LE, **ghi_de})
        except dependencies.AuthConfigError as exc:
            assert phan_thong_bao in str(exc), (
                f"{ten}: thong bao {str(exc)!r} khong nhac toi {phan_thong_bao!r}"
            )
        else:
            raise AssertionError(f"{ten}: khong bi chan")
    print(f"[PASS] ca {len(truong_hop)} cau hinh sai deu chet ngay luc nap")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_cau_hinh_hop_le_thi_nap_duoc,
        test_khoa_thieu_ngan_trung_va_bool_sai_deu_chet_ngay,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
