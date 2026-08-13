r"""Regression cho asset va UI shell dung chung cua Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_assets.py
"""
import base64
import hashlib
import os
import re
from types import SimpleNamespace
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from starlette.requests import Request

from review_platform.auth.rbac import Role


EXPECTED_HTMX_SHA384 = (
    "H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V"
)


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("198.51.100.20", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        }
    )


def test_vendor_htmx_dung_ban_da_khoa_va_static_phuc_vu_duoc():
    from review_platform.admin import rendering

    asset = rendering.STATIC_DIR / "vendor" / "htmx-2.0.10.min.js"
    digest = base64.b64encode(hashlib.sha384(asset.read_bytes()).digest()).decode()
    assert digest == EXPECTED_HTMX_SHA384

    assert asset.is_file() and asset.stat().st_size == 51238
    print("[PASS] HTMX vendored dung SHA-384 va dung bytes da khoa")


def test_rendering_helper_autoescape_va_base_chi_goi_script_local():
    from review_platform.admin import rendering

    user = SimpleNamespace(username="admin.demo", role=Role.ADMIN)
    response = rendering.render_template(
        _request("/admin"),
        "home.html",
        user=user,
        csrf_token="csrf-test",
    )
    html = response.body.decode("utf-8")
    assert 'src="/admin/static/vendor/htmx-2.0.10.min.js"' in html
    assert not re.search(r'<script[^>]+src="https?://', html)
    assert "admin.demo" in html
    assert ">admin<" in html

    escaped = rendering.render_template(
        _request("/admin/login"),
        "login.html",
        user=None,
        csrf_token="csrf-test",
        error='<script>alert("xss")</script>',
        flash=None,
    ).body.decode("utf-8")
    assert '<script>alert("xss")</script>' not in escaped
    assert "&lt;script&gt;" in escaped
    shell_messages = rendering.render_template(
        _request("/admin"),
        "home.html",
        user=user,
        csrf_token="csrf-test",
        flash="Đã cập nhật",
        error="Không thể tải",
    ).body.decode("utf-8")
    assert shell_messages.count('role="status"') == 1
    assert shell_messages.count('role="alert"') == 1
    assert "Đã cập nhật" in shell_messages
    assert "Không thể tải" in shell_messages
    print("[PASS] helper render autoescape, identity va chi dung HTMX local")


def test_nav_chi_tao_link_den_route_da_co_va_dung_role():
    from review_platform.admin import rendering

    user = SimpleNamespace(username="operator.demo", role=Role.OPERATOR)
    html = rendering.render_template(
        _request("/admin"),
        "home.html",
        user=user,
        csrf_token="csrf-test",
    ).body.decode("utf-8")
    hrefs = set(re.findall(r'href="([^"]+)"', html))
    assert "/admin" in hrefs
    assert "/admin/jobs" in hrefs
    assert "/admin/reviews" in hrefs
    assert "/admin/config-kb" in hrefs
    assert "/admin/evaluation" in hrefs
    assert "/admin/users" not in hrefs
    assert "/admin/change-password" in hrefs
    assert ">Tổng quan</a>" in html
    assert ">Trang chủ</a>" not in html
    assert not hrefs & {
        "/admin/users",
        "/admin/audit",
    }
    assert 'action="/admin/logout"' in html
    assert 'name="csrf_token" value="csrf-test"' in html
    admin_html = rendering.render_template(
        _request("/admin"),
        "home.html",
        user=SimpleNamespace(username="admin.demo", role=Role.ADMIN),
        csrf_token="csrf-test",
        view=None,
        filter_from="",
        filter_to="",
        error="qa",
    ).body.decode("utf-8")
    assert 'href="/admin/users"' in admin_html
    print("[PASS] nav chi link route da co, users chi admin va logout co CSRF")


def test_css_shell_co_accessibility_va_mobile_contract():
    from review_platform.admin import rendering

    css = (rendering.STATIC_DIR / "admin.css").read_text(encoding="utf-8")
    for token in ("--warning:", "--danger:", "--space-sm:", "--radius-sm:", "--content-max:"):
        assert token in css
    assert ":focus-visible" in css
    assert ".sr-only" in css
    assert re.search(r"@media\s*\(max-width:\s*(?:700px|43\.75rem)\)", css)
    assert "overflow-x: auto" in css
    mobile_css = css.split("@media (max-width: 43.75rem)", 1)[1]
    session_rule = mobile_css.split(".session-nav {", 1)[1].split("}", 1)[0]
    assert "display: grid" in session_rule
    assert "grid-template-columns: minmax(0, 1fr) auto" in session_rule
    identity_rule = mobile_css.split(".header-identity {", 1)[1].split("}", 1)[0]
    assert "grid-column: 1 / -1" in identity_rule
    logout_rule = mobile_css.split(".session-nav form {", 1)[1].split("}", 1)[0]
    assert "grid-column: 1" in logout_rule
    assert "prefers-reduced-motion" in css
    print("[PASS] CSS co focus, sr-only, mobile <=700px va reduced-motion")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_vendor_htmx_dung_ban_da_khoa_va_static_phuc_vu_duoc,
        test_rendering_helper_autoescape_va_base_chi_goi_script_local,
        test_nav_chi_tao_link_den_route_da_co_va_dung_role,
        test_css_shell_co_accessibility_va_mobile_contract,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
