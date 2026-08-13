r"""Security/integration test trang Config & KB read-only.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_read_only.py
"""
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies, read_only_sources, router
from review_platform.auth import users
from review_platform.auth.rbac import Role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_read_only"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"
EXPECTED_FILES = {
    "config/scoring.yaml",
    "src/agents/compliance_rules.json",
    "src/agents/brand_rules.json",
    "src/kb/specs.json",
}
EXPECTED_POLICY_HASHES = {
    "config/scoring.yaml": "6ca88fc2ad60e72fcdd162bbc0e55441d32841160db9563bf13ffdb7d81ebd49",
    "src/agents/compliance_rules.json": "edfd49d48e144f7e491ff8527650125370af72219e518222c4421c263ae4c6f6",
    "src/agents/brand_rules.json": "f4c9d489363c1471dafd99335d91cb0c44427c01a24789de0fa7f119ef443f9a",
    "src/kb/specs.json": "fe2185e06d64dcb237b8b49b683d42d4d3487f2bc7d1187de81e3b6ab05e6d61",
}


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _make_client(conn):
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
    return TestClient(app, follow_redirects=False, client=("198.51.100.83", 50000))


def _login(client, username: str, password: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def test_policy_loader_chi_doc_allowlist_va_metadata(conn):
    del conn
    assert not inspect.signature(read_only_sources.load_policy_files).parameters
    files = read_only_sources.load_policy_files()
    assert {item.relative_path for item in files} == EXPECTED_FILES
    assert all(re.fullmatch(r"[0-9a-f]{64}", item.sha256) for item in files)
    assert {item.relative_path: item.sha256 for item in files} == EXPECTED_POLICY_HASHES
    assert all(item.modified_at.utcoffset().total_seconds() == 0 for item in files)
    rendered = json.dumps(
        [item.metadata for item in files],
        ensure_ascii=False,
        default=str,
    )
    assert "tốt nhất" not in rendered
    assert "438km" not in rendered
    assert "nguon_kiem" not in rendered
    try:
        read_only_sources._resolve_allowed_path("../.env")
    except read_only_sources.UnsafePolicyPathError:
        pass
    else:
        raise AssertionError("loader chap nhan duong dan thoat khoi multiagent root")
    print("[PASS] policy loader chi doc allowlist va khong tra full corpus")


class _RecordingCursor:
    def __init__(self):
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, _params=None):
        self.sql = str(sql)

    def fetchall(self):
        return [
            (
                "kb_factcheck",
                "cam_nang",
                "vi",
                2,
                {
                    "model": "VF 9",
                    "verified": True,
                    "token": "KHONG-DUOC-LO",
                    "note": "Bearer cung-khong-duoc-lo",
                },
            )
        ]


class _RecordingConnection:
    def __init__(self):
        self.recording_cursor = _RecordingCursor()

    def cursor(self):
        return self.recording_cursor


def test_kb_query_khong_doc_document_vector_va_sanitize_excerpt(conn):
    del conn
    fake = _RecordingConnection()
    rows = read_only_sources.load_kb_summary(fake)
    sql = " ".join(fake.recording_cursor.sql.casefold().split())
    assert "document" not in sql
    assert not re.search(r"\b(?:k\.)?embedding\b", sql)
    assert rows[0].chunk_count == 2
    assert len(rows[0].metadata_excerpt) <= 500
    assert "KHONG-DUOC-LO" not in rows[0].metadata_excerpt
    assert "cung-khong-duoc-lo" not in rows[0].metadata_excerpt
    assert rows[0].embedding_model is None
    assert rows[0].embedding_dimension is None
    print("[PASS] KB query chi aggregate metadata da loc, khong doc noi dung/vector")


def test_route_viewer_read_only_path_query_bi_bo_qua_va_khong_lo_secret(conn):
    _reset_schema(conn)
    password = "Mat-khau-read-only-viewer-2026"
    viewer = users.create_user(
        conn,
        "read.only.viewer",
        password,
        Role.VIEWER,
        must_change_password=False,
    )
    secret_marker = "TOP-SECRET-REF-DO-NOT-RENDER"
    zero_vector = "[" + ",".join("0" for _ in range(1024)) + "]"
    with conn.cursor() as cur:
        cur.execute("UPDATE site SET secret_ref=%s", (secret_marker,))
        cur.execute(
            "INSERT INTO kb_chunk "
            "(collection,chunk_id,document,embedding,content_type,langcode,meta) "
            "VALUES (%s,%s,%s,%s::vector,%s,%s,%s::jsonb)",
            (
                "kb_factcheck",
                "test:1",
                "NOI-DUNG-KB-KHONG-DUOC-RENDER",
                zero_vector,
                "cam_nang",
                "vi",
                json.dumps(
                    {
                        "model": "VF 9",
                        "verified": True,
                        "secret_token": "TOKEN-KHONG-DUOC-RENDER",
                    }
                ),
            ),
        )

    client = _make_client(conn)
    assert _login(client, viewer.username, password).status_code == 303
    page = client.get("/admin/config-kb")
    traversal = client.get("/admin/config-kb?path=../../.env")
    assert page.status_code == traversal.status_code == 200
    assert page.text == traversal.text
    assert "Cấu hình &amp; KB" in page.text
    assert "cam-nang-vn" in page.text
    assert "kb_factcheck" in page.text
    assert "<dt>Số chunk</dt><dd>1</dd>" in page.text
    assert secret_marker not in page.text
    assert "NOI-DUNG-KB-KHONG-DUOC-RENDER" not in page.text
    assert "TOKEN-KHONG-DUOC-RENDER" not in page.text
    assert "ADMIN_CSRF_KEY" not in page.text
    assert "Save" not in page.text
    assert "<textarea" not in page.text
    assert "contenteditable" not in page.text
    post = client.post("/admin/config-kb", data={"csrf_token": "anything"})
    assert post.status_code == 405
    assert post.headers.get("allow") == "GET"
    print("[PASS] viewer doc config/KB; path query bi bo qua va route khong mutation")


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
            test_policy_loader_chi_doc_allowlist_va_metadata,
            test_kb_query_khong_doc_document_vector_va_sanitize_excerpt,
            test_route_viewer_read_only_path_query_bi_bo_qua_va_khong_lo_secret,
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
