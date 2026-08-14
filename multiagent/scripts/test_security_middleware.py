"""Test bien HTTP: security header, correlation ID va exception an toan.

Chay hoan toan tren app FastAPI toi gian, khong can Postgres.

Chay: .venv\\Scripts\\python.exe scripts\\test_security_middleware.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from review_platform import security as platform_security
from review_platform.api.limits import RequestSizeLimitMiddleware


def _app(*, environ=None, gioi_han=None):
    app = FastAPI()

    @app.get("/admin/thu")
    def admin_thu():
        return {"ok": True}

    @app.get("/api/v1/thu")
    def api_thu():
        return {"ok": True}

    @app.get("/admin/no")
    def admin_no():
        raise RuntimeError("chi tiet noi bo: /srv/app/secret.py dong 42")

    @app.get("/api/v1/no")
    def api_no():
        raise RuntimeError("chi tiet noi bo: postgresql://u:p@h/d")

    @app.post("/admin/nhan")
    def admin_nhan(body: dict):
        return {"nhan": len(str(body))}

    if gioi_han:
        app.add_middleware(RequestSizeLimitMiddleware, gioi_han=gioi_han)
    app.add_middleware(platform_security.SecurityMiddleware, environ=environ or {})
    return TestClient(app, raise_server_exceptions=False)


def test_moi_response_co_du_bo_security_header():
    client = _app()
    for duong_dan in ("/admin/thu", "/api/v1/thu"):
        phan_hoi = client.get(duong_dan)
        assert phan_hoi.status_code == 200, phan_hoi.text
        headers = phan_hoi.headers
        assert "default-src 'self'" in headers["content-security-policy"]
        assert "frame-ancestors 'none'" in headers["content-security-policy"]
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
    # Chi trang admin moi bat buoc no-store.
    assert client.get("/admin/thu").headers["cache-control"] == "no-store"
    print("[PASS] moi response co CSP/Referrer-Policy/nosniff/DENY; admin co no-store")


def test_hsts_chi_bat_khi_that_su_chay_https():
    """Bat HSTS tren HTTP local la noi doi, va khoa may dev vao HTTPS 6 thang."""
    assert "strict-transport-security" not in _app().get("/admin/thu").headers

    https = _app(environ={"VF_HTTPS_ONLY": "1"})
    assert "max-age=" in https.get("/admin/thu").headers["strict-transport-security"]
    print("[PASS] HSTS chi bat khi VF_HTTPS_ONLY=1, khong bat bua tren HTTP local")


def test_correlation_id_do_server_sinh_va_bo_qua_client():
    client = _app()
    gia_mao = "11111111-1111-1111-1111-111111111111"

    phan_hoi = client.get("/admin/thu", headers={"X-Request-ID": gia_mao})
    tra_ve = phan_hoi.headers["x-correlation-id"]

    assert tra_ve != gia_mao, "KHONG duoc dung ID do client gui"
    assert len(tra_ve) == 36, tra_ve

    # Hai request khac nhau phai co ID khac nhau.
    khac = client.get("/admin/thu").headers["x-correlation-id"]
    assert khac != tra_ve
    print("[PASS] correlation ID do server sinh, bo qua X-Request-ID cua client")


def test_exception_khong_bao_gio_lo_chi_tiet_noi_bo():
    client = _app()

    api = client.get("/api/v1/no")
    assert api.status_code == 500, api.status_code
    than = api.json()
    assert than["code"] == "internal_error"
    assert than["correlation_id"] == api.headers["x-correlation-id"]
    assert "postgresql" not in api.text and "RuntimeError" not in api.text

    admin = client.get("/admin/no")
    assert admin.status_code == 500
    assert "secret.py" not in admin.text and "Traceback" not in admin.text
    assert admin.headers["x-correlation-id"] in admin.text, (
        "trang loi phai hien ma doi chieu de tra log"
    )
    # Response loi VAN phai co security header.
    assert admin.headers["x-frame-options"] == "DENY"
    print("[PASS] exception tra ma chung + correlation, khong lo duong dan/DSN/traceback")


def test_admin_body_qua_64kib_bi_chan_truoc_form_parser():
    client = _app(gioi_han=(("/admin", platform_security.MAX_ADMIN_BODY),))

    vua = client.post("/admin/nhan", json={"x": "a" * 1000})
    assert vua.status_code == 200, vua.text

    qua = client.post("/admin/nhan", json={"x": "a" * (platform_security.MAX_ADMIN_BODY)})
    assert qua.status_code == 413, qua.status_code

    khong_khai_bao = client.post(
        "/admin/nhan",
        content=(chunk for chunk in [b"x" * 40000, b"y" * 40000]),
        headers={"Content-Type": "application/json"},
    )
    assert khong_khai_bao.status_code == 413, khong_khai_bao.status_code
    print("[PASS] admin body >64KiB bi 413 truoc parser, ke ca khi khong khai Content-Length")


def test_get_khong_bi_gioi_han_body_chan():
    """GET tra HTML lon khong duoc dinh vao limiter."""
    client = _app(gioi_han=(("/admin", 10),))
    assert client.get("/admin/thu").status_code == 200
    print("[PASS] GET khong bi limiter body chan du nguong rat nho")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_moi_response_co_du_bo_security_header,
        test_hsts_chi_bat_khi_that_su_chay_https,
        test_correlation_id_do_server_sinh_va_bo_qua_client,
        test_exception_khong_bao_gio_lo_chi_tiet_noi_bo,
        test_admin_body_qua_64kib_bi_chan_truoc_form_parser,
        test_get_khong_bi_gioi_han_body_chan,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
