"""Integration test HTTP cho Platform Admin routes.

Chay: .venv\\Scripts\\python.exe scripts\\test_admin_routes.py
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from review_platform import migrations
from review_platform.admin import dependencies, router
from review_platform.auth import sessions, throttle, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_routes"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
DEFAULT_SITE_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_PROFILE_ID = "00000000-0000-4000-8000-000000000002"
KNOWN_MODEL = "claude-haiku-4-5-20251001"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn, *, cookie_secure=False, raise_server_exceptions=True):
    app = FastAPI()
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=cookie_secure,
    )
    app.add_exception_handler(
        dependencies.AdminForbidden,
        router.forbidden_response,
    )
    app.include_router(router.router)
    app.mount(
        "/admin/static",
        StaticFiles(directory=router.STATIC_DIR),
        name="admin-static",
    )
    app.dependency_overrides[dependencies.get_db] = lambda: conn

    @app.get("/admin/operator-test")
    def operator_test(
        user=Depends(dependencies.require_role(Role.OPERATOR)),
    ):
        return {"username": user.username}

    return TestClient(
        app,
        follow_redirects=False,
        raise_server_exceptions=raise_server_exceptions,
        client=("198.51.100.20", 50000),
    )


def _login_csrf(client) -> str:
    response = client.get("/admin/login")
    assert response.status_code == 200, response.text
    return client.cookies.get(router.LOGIN_CSRF_COOKIE)


def _login(client, username, password):
    token = _login_csrf(client)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _session_csrf(conn, client) -> str:
    raw_token = client.cookies.get(router.SESSION_COOKIE)
    token_hash = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT csrf_secret FROM admin_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cur.fetchone()[0]


def _insert_dashboard_run(conn, index: int, *, is_fixture: bool):
    usage = [{"model": KNOWN_MODEL, "input_tokens": 1_000_000, "output_tokens": 0}]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO run_log ("
            "node_id, content_hash, scored_at, duration_ms, decision, final_score, "
            "agent_results, config_meta, usage, model, payload, site_id, profile_id, "
            "policy_version, external_content_id, content_type, langcode, "
            "correlation_id, writeback_status"
            ") VALUES ("
            "%s,%s,%s,1200,'publish',91,'{}'::jsonb,%s::jsonb,%s::jsonb,%s,"
            "'{}'::jsonb,%s,%s,'cam-nang-vn-v1',%s,'cam_nang','vi',%s,'succeeded'"
            ")",
            (
                f"dashboard-route-{index}",
                f"hash-dashboard-route-{index}",
                datetime(2026, 8, index, 12, tzinfo=timezone.utc),
                json.dumps({"is_fixture": is_fixture}),
                json.dumps(usage),
                KNOWN_MODEL,
                DEFAULT_SITE_ID,
                DEFAULT_PROFILE_ID,
                f"dashboard-route-{index}",
                uuid4(),
            ),
        )


def test_auth_config_fail_fast_key_thieu_ngan_trung_va_bool_sai(conn):
    valid = {
        "ADMIN_CSRF_KEY": "c" * 32,
        "ADMIN_THROTTLE_KEY": "t" * 32,
        "ADMIN_COOKIE_SECURE": "true",
    }
    loaded = dependencies.load_auth_config(valid)
    assert loaded.cookie_secure is True
    for changed, message in (
        ({"ADMIN_CSRF_KEY": ""}, "ADMIN_CSRF_KEY"),
        ({"ADMIN_THROTTLE_KEY": "short"}, "ADMIN_THROTTLE_KEY"),
        ({"ADMIN_THROTTLE_KEY": "c" * 32}, "khác nhau"),
        ({"ADMIN_COOKIE_SECURE": "sometimes"}, "true hoặc false"),
    ):
        with expect(dependencies.AuthConfigError, message):
            dependencies.load_auth_config({**valid, **changed})
    print("[PASS] auth config fail-fast voi key thieu/ngan/trung va bool sai")


def test_redirect_login_csrf_truoc_credential_va_wrong_password(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "route-user",
        "Mat-khau-route-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    unauthenticated = client.get("/admin")
    assert unauthenticated.status_code == 303
    assert unauthenticated.headers["location"] == "/admin/login"

    page = client.get("/admin/login")
    assert page.status_code == 200
    assert "Đăng nhập quản trị" in page.text
    assert "HttpOnly" in page.headers["set-cookie"]
    bad_csrf = client.post(
        "/admin/login",
        data={"username": "route-user", "password": "sai", "csrf_token": "sai"},
    )
    assert bad_csrf.status_code == 403
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 0

    token = _login_csrf(client)
    wrong = client.post(
        "/admin/login",
        data={
            "username": "route-user",
            "password": "Mat-khau-sai-2026",
            "csrf_token": token,
        },
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert wrong.status_code == 401
    limiter = throttle.LoginThrottle(conn, THROTTLE_KEY)
    with conn.cursor() as cur:
        cur.execute("SELECT subject_hash FROM admin_login_throttle")
        assert cur.fetchone()[0] == limiter.subject_hash(
            "route-user",
            "198.51.100.20",
        )
    print("[PASS] redirect, login CSRF truoc credential va bo qua X-Forwarded-For")


def test_login_csrf_chay_truoc_form_validation(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "csrf-order",
        "Mat-khau-csrf-order",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)

    missing_csrf = client.post(
        "/admin/login",
        data={
            "username": "csrf-order",
            "password": "Mat-khau-csrf-order",
        },
    )
    invalid_csrf_missing_credentials = client.post(
        "/admin/login",
        data={"csrf_token": "sai"},
    )
    assert missing_csrf.status_code == 403, missing_csrf.text
    assert invalid_csrf_missing_credentials.status_code == 403, (
        invalid_csrf_missing_credentials.text
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 0
    print("[PASS] login CSRF tra 403 truoc moi form/credential validation")


def test_login_tu_choi_password_qua_dai_truoc_argon2(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "oversized-password",
        "Mat-khau-hop-le-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    csrf_token = _login_csrf(client)
    original_verify = router.passwords.verify_password

    def must_not_verify(_hash_value, _password):
        raise AssertionError("password qua dai khong duoc dua vao Argon2")

    router.passwords.verify_password = must_not_verify
    try:
        response = client.post(
            "/admin/login",
            data={
                "username": "oversized-password",
                "password": "x" * 129,
                "csrf_token": csrf_token,
            },
        )
    finally:
        router.passwords.verify_password = original_verify

    assert response.status_code == 401, response.text
    assert "Thông tin đăng nhập không hợp lệ" in response.text
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_login_throttle")
        assert cur.fetchone()[0] == 1
    print("[PASS] login password >128 bi generic reject truoc Argon2")


def test_login_ok_cookie_flags_home_va_static(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "operator.user",
        "Mat-khau-operator-2026",
        Role.OPERATOR,
        must_change_password=False,
    )
    client = _make_client(conn)
    response = _login(client, "operator.user", "Mat-khau-operator-2026")
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    cookie = response.headers["set-cookie"]
    assert f"{router.SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/admin" in cookie

    home = client.get("/admin")
    assert home.status_code == 200
    assert "operator.user" in home.text and "operator" in home.text
    assert "Tổng quan vận hành" in home.text
    assert "Chưa có dữ liệu" in home.text
    assert "0 ms" not in home.text and "$0" not in home.text
    static = client.get("/admin/static/admin.css")
    assert static.status_code == 200
    assert "focus-visible" in static.text
    print("[PASS] login cookie flags, home that va static CSS")


def test_dashboard_date_validation_html_va_htmx_fragment(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "dashboard.viewer",
        "Mat-khau-dashboard-viewer",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    assert _login(client, "dashboard.viewer", "Mat-khau-dashboard-viewer").status_code == 303

    cases = (
        ("/admin?from=2026-08-01", "đồng thời"),
        ("/admin?from=01-08-2026&to=2026-08-02", "YYYY-MM-DD"),
        ("/admin?from=2026-08-03&to=2026-08-02", "không được trước"),
        ("/admin?from=2026-01-01&to=2026-04-04", "tối đa 93 ngày"),
    )
    for url, message in cases:
        response = client.get(url)
        assert response.status_code == 422, (url, response.status_code, response.text)
        assert response.headers["content-type"].startswith("text/html")
        assert "<!doctype html>" in response.text
        assert message in response.text
        assert '{"detail"' not in response.text

    fragment = client.get(
        "/admin?from=2026-08-03&to=2026-08-02",
        headers={"HX-Request": "true"},
    )
    assert fragment.status_code == 422
    assert "<html" not in fragment.text.lower()
    assert 'id="dashboard-metrics"' in fragment.text
    assert 'role="alert"' in fragment.text
    print("[PASS] dashboard date loi tra HTML/HTMX 422, khong roi ra JSON")


def test_dashboard_loai_fixture_va_render_metric_that(conn):
    _reset_schema(conn)
    users.create_user(
        conn,
        "dashboard.operator",
        "Mat-khau-dashboard-operator",
        Role.OPERATOR,
        must_change_password=False,
    )
    client = _make_client(conn)
    assert _login(
        client,
        "dashboard.operator",
        "Mat-khau-dashboard-operator",
    ).status_code == 303

    _insert_dashboard_run(conn, 1, is_fixture=True)
    fixture_only = client.get("/admin?from=2026-08-01&to=2026-08-02")
    assert fixture_only.status_code == 200
    assert "Chưa có dữ liệu" in fixture_only.text
    assert "0 ms" not in fixture_only.text and "$0" not in fixture_only.text
    assert "Đã loại dữ liệu fixture" in fixture_only.text

    _insert_dashboard_run(conn, 2, is_fixture=False)
    full = client.get("/admin?from=2026-08-01&to=2026-08-02")
    assert full.status_code == 200
    assert "1,000,000" in full.text
    assert "1,200.00 ms" in full.text
    assert "$1.00 USD" in full.text
    assert "ước tính" in full.text
    assert "Phiên bản giá 1" in full.text
    assert "15/10/2025" in full.text
    # Schema test chua co heartbeat va chua ai bam test connection, nen ca hai
    # phai bao "chua biet" - tuyet doi khong duoc mac dinh thanh khoe.
    assert "Không có heartbeat" in full.text, "worker phai bao chua co heartbeat"
    assert "Chưa kiểm tra bao giờ" in full.text, "connector phai bao chua kiem"
    assert "Đang chạy</dd>" not in full.text, "khong duoc bao worker khoe gia"
    assert 'action="/admin"' in full.text and 'method="get"' in full.text
    assert 'hx-get="/admin"' in full.text

    fragment = client.get(
        "/admin?from=2026-08-01&to=2026-08-02",
        headers={"HX-Request": "true"},
    )
    assert fragment.status_code == 200
    assert "<html" not in fragment.text.lower()
    assert 'id="dashboard-metrics"' in fragment.text
    print("[PASS] dashboard loai fixture, render metric that va HTMX partial")


def test_inactive_throttle_va_must_change_redirect(conn):
    _reset_schema(conn)
    inactive = users.create_user(
        conn,
        "inactive",
        "Mat-khau-inactive-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    users.set_active(conn, inactive.id, False)
    client = _make_client(conn)
    assert _login(client, "inactive", "Mat-khau-inactive-2026").status_code == 401

    forced = users.create_user(
        conn,
        "forced-change",
        "Mat-khau-forced-2026",
        Role.VIEWER,
        must_change_password=True,
    )
    login = _login(client, forced.username, "Mat-khau-forced-2026")
    assert login.status_code == 303
    assert login.headers["location"] == "/admin/change-password"
    blocked_home = client.get("/admin")
    assert blocked_home.status_code == 303
    assert blocked_home.headers["location"] == "/admin/change-password"

    client = _make_client(conn)
    for attempt in range(1, 6):
        response = _login(client, "khong-ton-tai", "Mat-khau-sai-2026")
        assert response.status_code == (429 if attempt == 5 else 401)
    print("[PASS] inactive bi tu choi, must-change bi ep route va fail thu 5 bi throttle")


def test_logout_csrf_revoke_va_viewer_bi_operator_gate(conn):
    _reset_schema(conn)
    user = users.create_user(
        conn,
        "viewer.user",
        "Mat-khau-viewer-2026",
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    assert _login(client, user.username, "Mat-khau-viewer-2026").status_code == 303
    forbidden = client.get("/admin/operator-test")
    assert forbidden.status_code == 403
    assert "<h1>Không có quyền truy cập</h1>" in forbidden.text
    assert client.post("/admin/logout", data={"csrf_token": "sai"}).status_code == 403

    csrf_token = _session_csrf(conn, client)
    logout = client.post("/admin/logout", data={"csrf_token": csrf_token})
    assert logout.status_code == 303
    assert logout.headers["location"] == "/admin/login"
    assert client.get("/admin").status_code == 303
    with conn.cursor() as cur:
        cur.execute(
            "SELECT revoked_at IS NOT NULL, revoke_reason FROM admin_session "
            "WHERE user_id=%s",
            (user.id,),
        )
        assert cur.fetchone() == (True, "logout")
    print("[PASS] logout bat CSRF/revoke va viewer bi operator gate 403")


def test_change_password_generic_error_revoke_va_bat_login_lai(conn):
    _reset_schema(conn)
    user = users.create_user(
        conn,
        "change.user",
        "Mat-khau-cu-2026",
        Role.VIEWER,
        must_change_password=True,
    )
    client = _make_client(conn)
    assert _login(client, user.username, "Mat-khau-cu-2026").status_code == 303
    csrf_token = _session_csrf(conn, client)
    mismatch = client.post(
        "/admin/change-password",
        data={
            "current_password": "Mat-khau-cu-2026",
            "new_password": "Mat-khau-moi-2026",
            "confirm_password": "khong-trung-2026",
            "csrf_token": csrf_token,
        },
    )
    assert mismatch.status_code == 400
    assert "Không thể đổi mật khẩu" in mismatch.text

    changed = client.post(
        "/admin/change-password",
        data={
            "current_password": "Mat-khau-cu-2026",
            "new_password": "Mat-khau-moi-2026",
            "confirm_password": "Mat-khau-moi-2026",
            "csrf_token": csrf_token,
        },
    )
    assert changed.status_code == 303
    assert changed.headers["location"] == "/admin/login"
    assert users.authenticate_candidate(conn, user.username, "Mat-khau-moi-2026")
    assert sessions.resolve(
        conn,
        client.cookies.get(router.SESSION_COOKIE, "missing"),
    ) is None
    login_page = client.get("/admin/login")
    assert "Đổi mật khẩu thành công" in login_page.text
    print("[PASS] change password dung generic error, revoke va bat login lai")


def test_login_lock_chan_reset_password_lot_qua_revoke_all(conn):
    _reset_schema(conn)
    old_password = "Mat-khau-race-old-2026"
    user = users.create_user(
        conn,
        "race.user",
        old_password,
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    csrf_token = _login_csrf(client)
    other_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with other_conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")

    verified = threading.Event()
    release_login = threading.Event()
    reset_started = threading.Event()
    reset_done = threading.Event()
    login_result = {}
    reset_result = {}
    original_verify = router.passwords.verify_password

    def blocking_verify(hash_value, password):
        result = original_verify(hash_value, password)
        if password == old_password and result:
            verified.set()
            if not release_login.wait(5):
                raise AssertionError("test timeout khi cho login tiep tuc")
        return result

    def run_login():
        try:
            login_result["response"] = client.post(
                "/admin/login",
                data={
                    "username": user.username,
                    "password": old_password,
                    "csrf_token": csrf_token,
                },
            )
        except Exception as exc:
            login_result["error"] = exc

    def run_reset():
        reset_started.set()
        try:
            users.reset_password(
                other_conn,
                user.id,
                "Mat-khau-race-new-2026",
            )
        except Exception as exc:
            reset_result["error"] = exc
        finally:
            reset_done.set()

    router.passwords.verify_password = blocking_verify
    login_thread = threading.Thread(target=run_login)
    reset_thread = threading.Thread(target=run_reset)
    reset_was_blocked = False
    try:
        login_thread.start()
        assert verified.wait(5), "login khong den diem verify"
        reset_thread.start()
        assert reset_started.wait(2)
        reset_was_blocked = not reset_done.wait(0.25)
    finally:
        release_login.set()
        login_thread.join(5)
        if reset_thread.ident is not None:
            reset_thread.join(5)
        router.passwords.verify_password = original_verify
        other_conn.close()

    assert not login_thread.is_alive() and not reset_thread.is_alive()
    assert "error" not in login_result, login_result
    assert "error" not in reset_result, reset_result
    assert reset_was_blocked, "reset-password khong cho row lock cua login"
    assert login_result["response"].status_code == 303
    raw_token = client.cookies.get(router.SESSION_COOKIE)
    assert sessions.resolve(conn, raw_token) is None
    print("[PASS] row lock serialize login voi reset va session moi bi revoke")


def test_login_lock_chan_change_password_lot_qua_revoke_all(conn):
    _reset_schema(conn)
    old_password = "Mat-khau-race-change-old"
    user = users.create_user(
        conn,
        "race.change.user",
        old_password,
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    csrf_token = _login_csrf(client)
    other_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with other_conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")

    verified = threading.Event()
    release_login = threading.Event()
    change_started = threading.Event()
    change_done = threading.Event()
    login_result = {}
    change_result = {}
    original_verify = router.passwords.verify_password

    def blocking_verify(hash_value, password):
        result = original_verify(hash_value, password)
        if (
            threading.current_thread() is not change_thread
            and password == old_password
            and result
        ):
            verified.set()
            if not release_login.wait(5):
                raise AssertionError("test timeout khi cho login tiep tuc")
        return result

    def run_login():
        try:
            login_result["response"] = client.post(
                "/admin/login",
                data={
                    "username": user.username,
                    "password": old_password,
                    "csrf_token": csrf_token,
                },
            )
        except Exception as exc:
            login_result["error"] = exc

    def run_change():
        change_started.set()
        try:
            users.change_password(
                other_conn,
                user.id,
                old_password,
                "Mat-khau-race-change-new",
            )
        except Exception as exc:
            change_result["error"] = exc
        finally:
            change_done.set()

    login_thread = threading.Thread(target=run_login)
    change_thread = threading.Thread(target=run_change)
    router.passwords.verify_password = blocking_verify
    change_was_blocked = False
    try:
        login_thread.start()
        assert verified.wait(5), "login khong den diem verify"
        change_thread.start()
        assert change_started.wait(2)
        change_was_blocked = not change_done.wait(0.25)
    finally:
        release_login.set()
        login_thread.join(5)
        if change_thread.ident is not None:
            change_thread.join(5)
        router.passwords.verify_password = original_verify
        other_conn.close()

    assert not login_thread.is_alive() and not change_thread.is_alive()
    assert "error" not in login_result, login_result
    assert "error" not in change_result, change_result
    assert change_was_blocked, "change-password khong cho row lock cua login"
    assert login_result["response"].status_code == 303
    raw_token = client.cookies.get(router.SESSION_COOKIE)
    assert sessions.resolve(conn, raw_token) is None
    print("[PASS] row lock serialize login voi change-password va revoke session moi")


def test_auth_state_change_va_audit_cung_transaction(conn):
    _reset_schema(conn)
    old_password = "Mat-khau-atomic-old-2026"
    new_password = "Mat-khau-atomic-new-2026"
    user = users.create_user(
        conn,
        "atomic.user",
        old_password,
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn, raise_server_exceptions=False)
    original_write_event = router.audit_log.write_event

    def reject_action(rejected_action):
        def fake_write_event(event_conn, *, action, **kwargs):
            if action is rejected_action:
                raise RuntimeError(f"audit unavailable: {action.value}")
            return original_write_event(event_conn, action=action, **kwargs)

        return fake_write_event

    token = _login_csrf(client)
    router.audit_log.write_event = reject_action(
        router.audit_log.AuditAction.LOGIN_SUCCESS
    )
    try:
        failed_login = client.post(
            "/admin/login",
            data={
                "username": user.username,
                "password": old_password,
                "csrf_token": token,
            },
        )
    finally:
        router.audit_log.write_event = original_write_event
    assert failed_login.status_code == 500
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_session WHERE user_id=%s", (user.id,))
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT last_login_at FROM admin_user WHERE id=%s", (user.id,))
        assert cur.fetchone()[0] is None

    assert _login(client, user.username, old_password).status_code == 303
    raw_token = client.cookies.get(router.SESSION_COOKIE)
    csrf_token = _session_csrf(conn, client)

    router.audit_log.write_event = reject_action(router.audit_log.AuditAction.LOGOUT)
    try:
        failed_logout = client.post(
            "/admin/logout",
            data={"csrf_token": csrf_token},
        )
    finally:
        router.audit_log.write_event = original_write_event
    assert failed_logout.status_code == 500
    assert sessions.resolve(conn, raw_token) is not None

    router.audit_log.write_event = reject_action(
        router.audit_log.AuditAction.PASSWORD_CHANGED
    )
    try:
        failed_change = client.post(
            "/admin/change-password",
            data={
                "current_password": old_password,
                "new_password": new_password,
                "confirm_password": new_password,
                "csrf_token": csrf_token,
            },
        )
    finally:
        router.audit_log.write_event = original_write_event
    assert failed_change.status_code == 500
    assert users.authenticate_candidate(conn, user.username, old_password)
    assert users.authenticate_candidate(conn, user.username, new_password) is None
    assert sessions.resolve(conn, raw_token) is not None
    print("[PASS] login/logout/change-password rollback neu audit that bai")


if __name__ == "__main__":
    try:
        connection = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        print(
            f"[SKIP] khong ket noi duoc Postgres ({exc.__class__.__name__}); "
            "[SKIP] khong phai [PASS]"
        )
        sys.exit(0)

    failed = False
    try:
        for fn in (
            test_auth_config_fail_fast_key_thieu_ngan_trung_va_bool_sai,
            test_redirect_login_csrf_truoc_credential_va_wrong_password,
            test_login_csrf_chay_truoc_form_validation,
            test_login_tu_choi_password_qua_dai_truoc_argon2,
            test_login_ok_cookie_flags_home_va_static,
            test_dashboard_date_validation_html_va_htmx_fragment,
            test_dashboard_loai_fixture_va_render_metric_that,
            test_inactive_throttle_va_must_change_redirect,
            test_logout_csrf_revoke_va_viewer_bi_operator_gate,
            test_change_password_generic_error_revoke_va_bat_login_lai,
            test_login_lock_chan_reset_password_lot_qua_revoke_all,
            test_login_lock_chan_change_password_lot_qua_revoke_all,
            test_auth_state_change_va_audit_cung_transaction,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
