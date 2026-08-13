r"""Security/integration test trang Evaluation read-only.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_admin_evaluation.py
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from review_platform import migrations
from review_platform.admin import dependencies, evaluation, router
from review_platform.auth import users
from review_platform.auth.rbac import Role


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_admin_evaluation"
CSRF_KEY = b"csrf-key-rieng-biet-du-32-byte-2026"
THROTTLE_KEY = b"throttle-key-rieng-biet-du-32-byte"


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
    return TestClient(app, follow_redirects=False, client=("198.51.100.84", 50000))


def _login(client, username: str, password: str):
    client.get("/admin/login")
    token = client.cookies.get(router.LOGIN_CSRF_COOKIE)
    return client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )


def _pending(experiment: str) -> dict:
    return {
        "experiment": experiment,
        "status": "pending",
        "score_path_snapshot": "04f10e1",
        "head_commit": None,
        "prompt_version": "020738e209017213",
        "model": "claude-haiku-4-5-20251001",
        "run_at": None,
        "evidence_path": None,
        "metadata_complete": False,
        "summary": "Chưa chạy.",
    }


def _valid_entries(relative_evidence: str) -> list[dict]:
    entries = [_pending(f"E{number}") for number in range(1, 7)]
    entries[1] = {
        "experiment": "E2",
        "status": "valid",
        "score_path_snapshot": "04f10e1",
        "head_commit": "a" * 40,
        "prompt_version": "not_applicable",
        "model": "BAAI/bge-m3",
        "run_at": "2026-08-13T16:06:44Z",
        "evidence_path": relative_evidence,
        "metadata_complete": True,
        "summary": "E2 đạt.",
    }
    return entries


def _write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_manifest_loader_validate_schema_provenance_va_path(conn):
    del conn
    manifest_path = EVIDENCE_DIR / ".test-evaluation-manifest.json"
    evidence_path = EVIDENCE_DIR / ".test-evaluation-e2.json"
    relative_evidence = "docs/evidence/.test-evaluation-e2.json"
    evidence_path.write_text('{"experiment":"E2"}\n', encoding="utf-8", newline="\n")
    try:
        entries = _valid_entries(relative_evidence)
        _write_json(manifest_path, entries)
        loaded = evaluation.load_manifest(manifest_path)
        assert [item.experiment for item in loaded] == [f"E{i}" for i in range(1, 7)]
        assert loaded[1].metadata_complete is True
        assert loaded[0].provenance_warning is not None
        assert loaded[1].evidence_file == evidence_path.resolve()

        invalid_cases = []

        duplicate = deepcopy(entries)
        duplicate.append(deepcopy(entries[1]))
        invalid_cases.append(duplicate)

        unknown_status = deepcopy(entries)
        unknown_status[0]["status"] = "running"
        invalid_cases.append(unknown_status)

        unknown_experiment = deepcopy(entries)
        unknown_experiment[0]["experiment"] = "E7"
        invalid_cases.append(unknown_experiment)

        absolute_path = deepcopy(entries)
        absolute_path[1]["evidence_path"] = str(evidence_path.resolve())
        invalid_cases.append(absolute_path)

        traversal = deepcopy(entries)
        traversal[1]["evidence_path"] = "docs/evidence/../.env"
        invalid_cases.append(traversal)

        environment_file = deepcopy(entries)
        environment_file[1]["evidence_path"] = "docs/evidence/.env"
        invalid_cases.append(environment_file)

        missing_file = deepcopy(entries)
        missing_file[1]["evidence_path"] = "docs/evidence/does-not-exist.json"
        invalid_cases.append(missing_file)

        pending_with_evidence = deepcopy(entries)
        pending_with_evidence[0]["evidence_path"] = relative_evidence
        invalid_cases.append(pending_with_evidence)

        pending_with_run = deepcopy(entries)
        pending_with_run[0]["run_at"] = "2026-08-13T00:00:00Z"
        invalid_cases.append(pending_with_run)

        complete_without_model = deepcopy(entries)
        complete_without_model[1]["model"] = None
        invalid_cases.append(complete_without_model)

        for index, invalid in enumerate(invalid_cases):
            _write_json(manifest_path, invalid)
            try:
                evaluation.load_manifest(manifest_path)
            except evaluation.ManifestError:
                pass
            else:
                raise AssertionError(f"manifest invalid case {index} khong bi chan")

        try:
            evaluation.load_manifest(REPO_ROOT / "README.md")
        except evaluation.ManifestError:
            pass
        else:
            raise AssertionError("loader chap nhan manifest ngoai docs/evidence")
    finally:
        manifest_path.unlink(missing_ok=True)
        evidence_path.unlink(missing_ok=True)
    print("[PASS] manifest chan duplicate/status/path/provenance sai")


def test_evaluation_route_viewer_read_only_va_evidence_allowlist(conn):
    _reset_schema(conn)
    password = "Mat-khau-evaluation-viewer-2026"
    viewer = users.create_user(
        conn,
        "evaluation.viewer",
        password,
        Role.VIEWER,
        must_change_password=False,
    )
    client = _make_client(conn)
    assert _login(client, viewer.username, password).status_code == 303

    page = client.get("/admin/evaluation")
    assert page.status_code == 200
    assert "Đánh giá" in page.text
    assert all(f">E{number}<" in page.text for number in range(1, 7))
    assert "không phải kết quả code hiện hành" in page.text
    assert "Provenance chưa đầy đủ" in page.text
    assert "Chạy E1" not in page.text and "Chạy E5" not in page.text
    assert 'action="/admin/evaluation' not in page.text
    assert client.post("/admin/evaluation").status_code == 405

    e2 = client.get("/admin/evaluation/evidence/E2")
    e2_with_query = client.get(
        "/admin/evaluation/evidence/E2?path=../../.env"
    )
    assert e2.status_code == e2_with_query.status_code == 200
    assert e2.content == e2_with_query.content
    assert e2.headers["content-type"].startswith("application/json")
    assert e2.headers["x-content-type-options"] == "nosniff"
    assert e2.headers["cache-control"] == "no-store"
    assert json.loads(e2.content)["experiment"] == "E2"

    e4 = client.get("/admin/evaluation/evidence/E4")
    assert e4.status_code == 200
    assert e4.headers["content-type"].startswith("text/plain")
    assert e4.headers["x-content-type-options"] == "nosniff"
    assert e4.headers["cache-control"] == "no-store"

    assert client.get("/admin/evaluation/evidence/E1").status_code == 404
    assert client.get("/admin/evaluation/evidence/E7").status_code == 404
    assert client.get("/admin/evaluation/evidence/..%2F..%2F.env").status_code == 404
    assert client.post("/admin/evaluation/evidence/E2").status_code == 405
    print("[PASS] viewer doc evaluation/evidence allowlist; route khong mutation")


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
            test_manifest_loader_validate_schema_provenance_va_path,
            test_evaluation_route_viewer_read_only_va_evidence_allowlist,
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
