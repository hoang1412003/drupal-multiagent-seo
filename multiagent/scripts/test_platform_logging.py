"""Test che secret de quy va log co cau truc (Plan 5 Task 2).

Trong tam: secret hiem khi nam o tang mot. Test nay chu yeu kiem cac tang
LONG NHAU va cac gia tri KHONG co ten khoa goi y - do la cho ma mot ham che
so sai se de dang bo lot.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_logging.py
"""
import json
import logging as stdlib_logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform.logging import (
    DA_CHE,
    MAX_ITEMS,
    MAX_STRING,
    RedactingFilter,
    event,
    redact,
)


TOKEN = "sk-live-abcdef0123456789abcdef0123456789"


def test_che_theo_ten_khoa_o_moi_tang():
    goc = {
        "safe": "giu nguyen",
        "Authorization": f"Bearer {TOKEN}",
        "request": {
            "headers": {"Cookie": "session=abc", "X-Api-Key": TOKEN},
            "body": {"user": {"PASSWORD": "matkhau", "email": "a@b.c"}},
        },
        "db": {"database_url": "postgresql://u:p@h/d"},
    }
    ket = redact(goc)

    assert ket["safe"] == "giu nguyen"
    assert ket["Authorization"] == DA_CHE
    assert ket["request"]["headers"]["Cookie"] == DA_CHE
    assert ket["request"]["headers"]["X-Api-Key"] == DA_CHE
    assert ket["request"]["body"]["user"]["PASSWORD"] == DA_CHE
    assert ket["request"]["body"]["user"]["email"] == "a@b.c"
    assert ket["db"]["database_url"] == DA_CHE
    # Token khong duoc con sot o BAT KY dau trong ket qua.
    assert TOKEN not in json.dumps(ket)

    # Ba cach viet cua CUNG mot khai niem deu phai dinh. Header HTTP that dung
    # gach noi, config dung gach duoi, code dung lien - bo sot mot dang la du
    # de lo token trong log production.
    bien_the = redact({
        "X-Api-Key": TOKEN, "api_key": TOKEN, "apikey": TOKEN,
        "Database-URL": "postgresql://u:p@h/d", "DATABASE_URL": "x",
        "Set-Cookie": "a=b", "X-Auth-Token": TOKEN,
    })
    assert set(bien_the.values()) == {DA_CHE}, bien_the
    print("[PASS] che theo ten khoa o moi tang, moi cach viet gach noi/duoi/lien")


def test_che_theo_hinh_dang_gia_tri_du_ten_khoa_vo_hai():
    """Cho de bo lot nhat: message tu do, ten khoa khong goi y gi."""
    goc = {
        "message": f"goi that bai voi header Authorization: Bearer {TOKEN}",
        "note": "postgresql://vf_agent:matkhau_that@127.0.0.1:5433/vf_agent",
        "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefgh",
        "danh_sach": [f"Basic {TOKEN}", "chuoi vo hai"],
    }
    ket = redact(goc)
    tat_ca = json.dumps(ket)

    assert TOKEN not in tat_ca, ket
    assert "matkhau_that" not in tat_ca, ket
    assert "eyJhbGciOiJIUzI1NiJ9" not in tat_ca, ket
    assert DA_CHE in ket["message"]
    assert ket["danh_sach"][1] == "chuoi vo hai"
    print("[PASS] che theo hinh dang Bearer/Basic/JWT/DSN du ten khoa vo hai")


def test_khong_sua_doi_tuong_goc():
    goc = {"token": "bi-mat", "nested": {"list": [{"password": "x"}]}}
    ban_sao = json.dumps(goc, sort_keys=True)

    redact(goc)

    assert json.dumps(goc, sort_keys=True) == ban_sao, "redact da sua object goc"
    print("[PASS] redact tra ban sao, khong sua doi tuong goc")


def test_gioi_han_do_dai_so_luong_va_do_sau():
    dai = "x" * (MAX_STRING + 500)
    assert redact(dai).endswith("...[cat]")
    assert len(redact(dai)) < MAX_STRING + 20

    nhieu = list(range(MAX_ITEMS + 50))
    ket = redact(nhieu)
    assert len(ket) == MAX_ITEMS + 1, len(ket)
    assert "con 50 phan tu" in ket[-1]

    sau = {"a": {}}
    con = sau["a"]
    for _ in range(12):
        con["a"] = {}
        con = con["a"]
    con["token"] = "bi-mat"
    assert "bi-mat" not in json.dumps(redact(sau))
    print("[PASS] cat chuoi/collection/do sau, secret o tang sau van khong lot")


def test_gia_tri_an_toan_van_dung_duoc_sau_khi_che():
    """Che qua tay cung la loi: mat luon kha nang chan doan."""
    goc = {
        "job_id": "40ce0ff2-a55e-4507-bb44-a2ff64cd3e22",
        "content_hash": "5f0a2658ef2667084b4af92e8c147da9617e1f3a9f3bf4901a24fa1d48618333",
        "token_prefix": "CytljZjjg9EX",
        "site_slug": "drupal-vn-primary",
        "revision": "93",
        "status_code": 409,
    }
    ket = redact(goc)
    assert ket["job_id"] == goc["job_id"]
    assert ket["content_hash"] == goc["content_hash"]
    assert ket["site_slug"] == "drupal-vn-primary"
    assert ket["status_code"] == 409
    # `token_prefix` co chua chu "token" nen bi che - dung, vi quy tac theo ten
    # khoa phai fail-closed. Muon log prefix thi dat ten khac.
    assert ket["token_prefix"] == DA_CHE
    print("[PASS] ID/hash/slug/ma HTTP van dung duoc; ten co 'token' fail-closed")


def test_event_ghi_dung_mot_dong_json():
    ban_ghi = []

    class LoggerGia:
        def info(self, msg):
            ban_ghi.append(msg)

    event(LoggerGia(), "job_failed", job_id="abc", authorization=f"Bearer {TOKEN}")

    assert len(ban_ghi) == 1, ban_ghi
    assert "\n" not in ban_ghi[0], "phai la DUNG mot dong"
    doc_lai = json.loads(ban_ghi[0])
    assert doc_lai["event"] == "job_failed"
    assert doc_lai["job_id"] == "abc"
    assert doc_lai["authorization"] == DA_CHE
    assert TOKEN not in ban_ghi[0]
    print("[PASS] event() ghi dung mot dong JSON hop le va da che")


def test_filter_che_ca_log_khong_qua_event():
    """Thu vien ben thu ba khong biet quy uoc cua du an - filter phai bat."""
    record = stdlib_logging.LogRecord(
        name="requests", level=stdlib_logging.WARNING, pathname="x", lineno=1,
        msg=f"loi khi goi voi Authorization: Bearer {TOKEN}", args=(), exc_info=None,
    )
    assert RedactingFilter().filter(record) is True
    assert TOKEN not in str(record.msg), record.msg

    # Filter hong khong duoc lam mat dong log.
    class MsgHong:
        def __str__(self):
            raise RuntimeError("khong str duoc")

    hong = stdlib_logging.LogRecord(
        name="x", level=20, pathname="x", lineno=1, msg=MsgHong(), args=(),
        exc_info=None,
    )
    assert RedactingFilter().filter(hong) is True
    print("[PASS] filter che ca log thu vien ngoai va khong bao gio nuot dong log")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_che_theo_ten_khoa_o_moi_tang,
        test_che_theo_hinh_dang_gia_tri_du_ten_khoa_vo_hai,
        test_khong_sua_doi_tuong_goc,
        test_gioi_han_do_dai_so_luong_va_do_sau,
        test_gia_tri_an_toan_van_dung_duoc_sau_khi_che,
        test_event_ghi_dung_mot_dong_json,
        test_filter_che_ca_log_khong_qua_event,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
