r"""Integration test UI quan ly tai khoan Platform Admin.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_user_routes.py
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from review_platform import migrations
from review_platform.admin import dependencies, queries, router, user_routes
from review_platform.auth import audit_log, sessions, users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_user_routes"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn, *, raise_server_exceptions=True):
    app = FastAPI()
    app.state.auth_config = dependencies.AuthConfig(
        csrf_key=CSRF_KEY,
        throttle_key=THROTTLE_KEY,
        cookie_secure=False,
    )
    app.add_exception_handler(dependencies.AdminForbidden, router.forbidden_response)
    app.include_router(router.router)
    app.mount(
        "/admin/static",
        StaticFiles(directory=router.STATIC_DIR),
        name="admin-static",
    )
    app.dependency_overrides[dependencies.get_db] = lambda: conn
    return TestClient(
        app,
        follow_redirects=False,
        raise_server_exceptions=raise_server_exceptions,
        client=("198.51.100.80", 50000),
    )


def _login(client, username: str, password: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _session_csrf(conn, client):
    raw = client.cookies.get(router.SESSION_COOKIE)
    token_hash = hashlib.sha256(raw.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT csrf_secret FROM admin_session WHERE token_hash=%s",
            (token_hash,),
        )
        return cur.fetchone()[0]


def _user(conn, username: str, role: Role, *, active=True):
    created = users.create_user(
        conn,
        username,
        f"Mat-khau-{username}-2026",
        role,
        must_change_password=False,
    )
    if not active:
        return users.set_active(conn, created.id, False)
    return created


def test_list_users_sort_pagination_va_khong_lo_password(conn):
    _reset_schema(conn)
    first = _user(conn, "first.user", Role.VIEWER)
    second = _user(conn, "second.user", Role.OPERATOR)
    third = _user(conn, "third.user", Role.ADMIN)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE admin_user SET created_at='2026-08-01 00:00:00+00' "
            "WHERE id IN (%s,%s,%s)",
            (first.id, second.id, third.id),
        )
        cur.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")
    page = queries.list_users(conn, page=1, page_size=2)
    assert page.total == 3 and page.total_pages == 2
    expected_ids = tuple(sorted((first.id, second.id, third.id), reverse=True))
    assert tuple(item.id for item in page.items) == expected_ids[:2]
    assert not hasattr(page.items[0], "password_hash")
    assert page.items[0].created_at.utcoffset().total_seconds() == 0
    second_page = queries.list_users(conn, page=2, page_size=2)
    assert [item.id for item in second_page.items] == [expected_ids[2]]
    for args in ((0, 25), (1, 0), (1, 101)):
        try:
            queries.list_users(conn, page=args[0], page_size=args[1])
        except ValueError:
            pass
        else:
            raise AssertionError("list_users khong chan pagination sai")
    print("[PASS] users query stable pagination/UTC va khong co password hash")


def test_users_admin_only_va_invalid_input_html(conn):
    _reset_schema(conn)
    viewer = _user(conn, "route.viewer", Role.VIEWER)
    operator = _user(conn, "route.operator", Role.OPERATOR)
    admin = _user(conn, "route.admin", Role.ADMIN)
    clients = []
    for account in (viewer, operator):
        client = _make_client(conn)
        assert _login(
            client,
            account.username,
            f"Mat-khau-{account.username}-2026",
        ).status_code == 303
        clients.append((client, _session_csrf(conn, client)))
        assert client.get("/admin/users").status_code == 403
        denied = client.post(
            "/admin/users",
            data={
                "csrf_token": clients[-1][1],
                "username": "forbidden.create",
                "role": "viewer",
            },
        )
        assert denied.status_code == 403

    client = _make_client(conn)
    assert _login(client, admin.username, "Mat-khau-route.admin-2026").status_code == 303
    csrf = _session_csrf(conn, client)
    listing = client.get("/admin/users")
    assert listing.status_code == 200 and "Người dùng" in listing.text
    assert "password_hash" not in listing.text
    assert client.get("/admin/users/not-a-uuid/role").status_code in {404, 405}
    bad_role = client.post(
        f"/admin/users/{viewer.id}/role",
        data={"csrf_token": csrf, "role": "superadmin"},
    )
    assert bad_role.status_code == 400
    assert bad_role.headers["content-type"].startswith("text/html")
    bad_uuid = client.post(
        "/admin/users/not-a-uuid/lock",
        data={"csrf_token": csrf},
    )
    assert bad_uuid.status_code == 404
    missing = client.post(
        f"/admin/users/{UUID('00000000-0000-4000-8000-000000000099')}/unlock",
        data={"csrf_token": csrf},
    )
    assert missing.status_code == 404
    no_csrf = client.post(
        f"/admin/users/{viewer.id}/lock",
        data={},
    )
    assert no_csrf.status_code == 403
    print("[PASS] users route admin-only, CSRF va invalid input tra HTML an toan")


def test_create_reset_password_one_time_no_store_va_audit(conn):
    _reset_schema(conn)
    admin = _user(conn, "password.admin", Role.ADMIN)
    client = _make_client(conn)
    assert _login(
        client,
        admin.username,
        "Mat-khau-password.admin-2026",
    ).status_code == 303
    csrf = _session_csrf(conn, client)
    generated = iter(("Temporary-create-2026", "Temporary-reset-2026"))
    original_token = user_routes._generate_temporary_password
    user_routes._generate_temporary_password = lambda: next(generated)
    try:
        created_response = client.post(
            "/admin/users",
            data={
                "csrf_token": csrf,
                "username": "  New.User  ",
                "role": "operator",
            },
        )
        assert created_response.status_code == 201
        assert "Temporary-create-2026" in created_response.text
        assert created_response.headers["cache-control"] == "no-store, private"
        assert created_response.headers["pragma"] == "no-cache"
        created = users.find_by_username(conn, "new.user")
        assert created.username == "New.User"
        assert created.role is Role.OPERATOR and created.must_change_password is True
        assert users.authenticate_candidate(
            conn,
            "new.user",
            "Temporary-create-2026",
        )

        listing = client.get("/admin/users")
        assert "Temporary-create-2026" not in listing.text
        new_form = client.get("/admin/users/new")
        assert "Temporary-create-2026" not in new_form.text

        issued = sessions.issue(conn, created.id)
        reset_response = client.post(
            f"/admin/users/{created.id}/reset-password",
            data={"csrf_token": csrf},
        )
        assert reset_response.status_code == 200
        assert "Temporary-reset-2026" in reset_response.text
        assert reset_response.headers["cache-control"] == "no-store, private"
        assert reset_response.headers["pragma"] == "no-cache"
        assert sessions.resolve(conn, issued.raw_token) is None
        assert users.authenticate_candidate(
            conn,
            "new.user",
            "Temporary-reset-2026",
        )
    finally:
        user_routes._generate_temporary_password = original_token

    with conn.cursor() as cur:
        cur.execute(
            "SELECT action,metadata::text FROM admin_audit_log ORDER BY id"
        )
        audit_text = json.dumps(cur.fetchall(), default=str)
    assert "user_created" in audit_text and "password_reset" in audit_text
    assert "Temporary-create-2026" not in audit_text
    assert "Temporary-reset-2026" not in audit_text
    assert "Temporary-reset-2026" not in client.get("/admin/users").text
    print("[PASS] create/reset chi lo password mot response no-store, audit khong luu")


def test_role_lock_unlock_audit_va_last_admin_denied(conn):
    _reset_schema(conn)
    admin = _user(conn, "mutation.admin", Role.ADMIN)
    target = _user(conn, "mutation.target", Role.VIEWER)
    client = _make_client(conn)
    assert _login(
        client,
        admin.username,
        "Mat-khau-mutation.admin-2026",
    ).status_code == 303
    csrf = _session_csrf(conn, client)

    role_response = client.post(
        f"/admin/users/{target.id}/role",
        data={"csrf_token": csrf, "role": "operator"},
    )
    assert role_response.status_code == 303
    assert users.get_user(conn, target.id).role is Role.OPERATOR
    assert client.post(
        f"/admin/users/{target.id}/lock",
        data={"csrf_token": csrf},
    ).status_code == 303
    assert users.get_user(conn, target.id).active is False
    assert client.post(
        f"/admin/users/{target.id}/unlock",
        data={"csrf_token": csrf},
    ).status_code == 303
    assert users.get_user(conn, target.id).active is True

    denied_lock = client.post(
        f"/admin/users/{admin.id}/lock",
        data={"csrf_token": csrf},
    )
    assert denied_lock.status_code == 409
    assert users.get_user(conn, admin.id).active is True
    denied_role = client.post(
        f"/admin/users/{admin.id}/role",
        data={"csrf_token": csrf, "role": "viewer"},
    )
    assert denied_role.status_code == 409
    assert users.get_user(conn, admin.id).role is Role.ADMIN
    with conn.cursor() as cur:
        cur.execute("SELECT action,outcome,metadata FROM admin_audit_log ORDER BY id")
        events = cur.fetchall()
    assert ("user_role_changed", "success") in {(row[0], row[1]) for row in events}
    assert ("user_locked", "success") in {(row[0], row[1]) for row in events}
    assert ("user_unlocked", "success") in {(row[0], row[1]) for row in events}
    denied = [row for row in events if row[0] == "last_admin_denied"]
    assert {row[2]["operation"] for row in denied} == {"lock", "set-role"}
    print("[PASS] role/lock/unlock audit va last-admin denied tra 409")


def test_audit_failure_rollback_moi_mutation(conn):
    _reset_schema(conn)
    admin = _user(conn, "atomic.admin", Role.ADMIN)
    target = _user(conn, "atomic.target", Role.VIEWER)
    inactive = _user(conn, "atomic.inactive", Role.VIEWER, active=False)
    client = _make_client(conn, raise_server_exceptions=False)
    assert _login(client, admin.username, "Mat-khau-atomic.admin-2026").status_code == 303
    csrf = _session_csrf(conn, client)
    original_write = user_routes.audit_log.write_event
    original_token = user_routes._generate_temporary_password
    user_routes._generate_temporary_password = lambda: "Temporary-atomic-2026"

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    user_routes.audit_log.write_event = fail_audit
    try:
        responses = (
            client.post(
                "/admin/users",
                data={"csrf_token": csrf, "username": "atomic.created", "role": "viewer"},
            ),
            client.post(
                f"/admin/users/{target.id}/role",
                data={"csrf_token": csrf, "role": "operator"},
            ),
            client.post(
                f"/admin/users/{target.id}/lock",
                data={"csrf_token": csrf},
            ),
            client.post(
                f"/admin/users/{inactive.id}/unlock",
                data={"csrf_token": csrf},
            ),
        )
        issued = sessions.issue(conn, target.id)
        reset_response = client.post(
            f"/admin/users/{target.id}/reset-password",
            data={"csrf_token": csrf},
        )
    finally:
        user_routes.audit_log.write_event = original_write
        user_routes._generate_temporary_password = original_token

    assert all(response.status_code == 500 for response in responses)
    assert reset_response.status_code == 500
    assert users.find_by_username(conn, "atomic.created") is None
    assert users.get_user(conn, target.id).role is Role.VIEWER
    assert users.get_user(conn, target.id).active is True
    assert users.get_user(conn, inactive.id).active is False
    assert users.authenticate_candidate(
        conn,
        target.username,
        "Mat-khau-atomic.target-2026",
    )
    assert sessions.resolve(conn, issued.raw_token) is not None
    print("[PASS] audit fail rollback create/role/lock/unlock/reset va session")


def test_hai_request_khong_vo_hieu_het_admin(conn):
    _reset_schema(conn)
    admin_a = _user(conn, "race.web.a", Role.ADMIN)
    admin_b = _user(conn, "race.web.b", Role.ADMIN)
    conn_b = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn_b.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    client_a = _make_client(conn)
    client_b = _make_client(conn_b)
    assert _login(client_a, admin_a.username, "Mat-khau-race.web.a-2026").status_code == 303
    assert _login(client_b, admin_b.username, "Mat-khau-race.web.b-2026").status_code == 303
    csrf_a = _session_csrf(conn, client_a)
    csrf_b = _session_csrf(conn_b, client_b)

    barrier = threading.Barrier(2)
    original_set_active = user_routes.users.set_active

    def synchronized_set_active(target_conn, user_id, active):
        barrier.wait(timeout=5)
        return original_set_active(target_conn, user_id, active)

    user_routes.users.set_active = synchronized_set_active
    results = []

    def lock(client, csrf, user_id):
        results.append(
            client.post(
                f"/admin/users/{user_id}/lock",
                data={"csrf_token": csrf},
            ).status_code
        )

    threads = (
        threading.Thread(target=lock, args=(client_a, csrf_a, admin_a.id)),
        threading.Thread(target=lock, args=(client_b, csrf_b, admin_b.id)),
    )
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
    finally:
        user_routes.users.set_active = original_set_active
        conn_b.close()
    assert not any(thread.is_alive() for thread in threads)
    assert sorted(results) == [303, 409], results
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM admin_user WHERE active AND role='admin'")
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT count(*) FROM admin_audit_log WHERE action='last_admin_denied'")
        assert cur.fetchone()[0] == 1
    print("[PASS] hai request web dong thoi van giu mot active admin")


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
            test_list_users_sort_pagination_va_khong_lo_password,
            test_users_admin_only_va_invalid_input_html,
            test_create_reset_password_one_time_no_store_va_audit,
            test_role_lock_unlock_audit_va_last_admin_denied,
            test_audit_failure_rollback_moi_mutation,
            test_hai_request_khong_vo_hieu_het_admin,
        ):
            try:
                fn(connection)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
    finally:
        with connection.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC'")
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        connection.close()

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
