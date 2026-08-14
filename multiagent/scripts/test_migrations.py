"""Test migration runner SQL co version va checksum.

Phan discovery chay hoan toan khong can Postgres. Cac integration test schema
se duoc bo sung o Task 2 va phai ghi ro [SKIP] neu DB local chua san sang.

Chay: .venv\\Scripts\\python.exe scripts\\test_migrations.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import database, migrations


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SITE_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_PROFILE_ID = "00000000-0000-4000-8000-000000000002"


@contextmanager
def expect(exc_type, message: str):
    """Bat dung loai exception va mot doan message, khong can test framework."""
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def test_discover_sap_xep_va_checksum_canonical():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0002_second.sql").write_bytes(b"SELECT 2;\r\n")
        (root / "0001_first.sql").write_bytes(b"SELECT 1;\n")

        found = migrations.discover(root)

        assert [m.version for m in found] == [1, 2], found
        assert [m.name for m in found] == ["first", "second"], found
        assert found[0].checksum == hashlib.sha256(b"SELECT 1;\n").hexdigest()
        assert found[1].checksum == hashlib.sha256(b"SELECT 2;\n").hexdigest()
    print("[PASS] discover sap xep version va bam noi dung LF canonical")


def test_discover_checksum_khong_phu_thuoc_lf_hay_crlf():
    with tempfile.TemporaryDirectory() as lf_tmp, tempfile.TemporaryDirectory() as crlf_tmp:
        lf_root = Path(lf_tmp)
        crlf_root = Path(crlf_tmp)
        (lf_root / "0001_first.sql").write_bytes(b"SELECT 1;\nSELECT 2;\n")
        (crlf_root / "0001_first.sql").write_bytes(
            b"SELECT 1;\r\nSELECT 2;\r\n"
        )

        lf_checksum = migrations.discover(lf_root)[0].checksum
        crlf_checksum = migrations.discover(crlf_root)[0].checksum

        assert lf_checksum == crlf_checksum, (lf_checksum, crlf_checksum)
    print("[PASS] checksum migration khong doi khi Git checkout LF/CRLF")


def test_status_chap_nhan_checksum_crlf_lich_su_nhung_van_chan_sua_sql():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        migration = root / "0001_first.sql"
        lf_content = b"SELECT 1;\nSELECT 2;\n"
        crlf_content = lf_content.replace(b"\n", b"\r\n")
        migration.write_bytes(lf_content)
        conn = FakeConnection()
        conn.history[1] = (
            "first",
            hashlib.sha256(crlf_content).hexdigest(),
        )

        current = migrations.status(conn, root)
        assert current.applied == (1,) and current.pending == (), current

        migration.write_bytes(b"SELECT 1;\nSELECT 3;\n")
        with expect(migrations.MigrationError, "checksum khong khop version 0001"):
            migrations.status(conn, root)
    print("[PASS] checksum CRLF lich su tuong thich nhung semantic edit van bi chan")


def test_discover_chan_version_trung():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
        (root / "0001_duplicate.sql").write_text("SELECT 2;", encoding="utf-8")

        with expect(migrations.MigrationError, "trung version 0001"):
            migrations.discover(root)
    print("[PASS] discover chan hai file trung version")


def test_discover_chan_ten_file_sql_sai_quy_uoc():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "1_wrong.sql").write_text("SELECT 1;", encoding="utf-8")

        with expect(migrations.MigrationError, "ten migration khong hop le"):
            migrations.discover(root)
    print("[PASS] discover chan file SQL sai quy uoc ten")


def test_discover_chan_khoang_trong_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
        (root / "0003_third.sql").write_text("SELECT 3;", encoding="utf-8")

        with expect(migrations.MigrationError, "thieu version 0002"):
            migrations.discover(root)
    print("[PASS] discover chan khoang trong chuoi version")


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        compact = " ".join(str(sql).split()).lower()
        if compact.startswith("create table if not exists schema_migration"):
            self.conn.history_ready = True
        elif compact.startswith("select version, name, checksum from schema_migration"):
            self.rows = [
                (version, name, checksum)
                for version, (name, checksum) in sorted(self.conn.history.items())
            ]
        elif compact.startswith("insert into schema_migration"):
            version, name, checksum = params
            if version in self.conn.history:
                raise RuntimeError(f"duplicate schema_migration {version}")
            self.conn.history[version] = (name, checksum)
        else:
            self.conn.executed_scripts.append(str(sql))
            if "RAISE_FAKE" in str(sql):
                raise RuntimeError("migration script that bai")

    def fetchall(self):
        return list(self.rows)


class FakeTransaction:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.snapshot = (
            dict(self.conn.history),
            list(self.conn.executed_scripts),
        )
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self.conn.history, self.conn.executed_scripts = self.snapshot
        return False


class FakeConnection:
    def __init__(self):
        self.history_ready = False
        self.history = {}
        self.executed_scripts = []

    def cursor(self):
        return FakeCursor(self)

    def transaction(self):
        return FakeTransaction(self)


def test_status_apply_require_current_va_checksum_guard():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = root / "0001_first.sql"
        second = root / "0002_second.sql"
        first.write_text("SELECT 'one';", encoding="utf-8")
        second.write_text("SELECT 'two';", encoding="utf-8")
        conn = FakeConnection()

        before = migrations.status(conn, root)
        assert before.applied == () and before.pending == (1, 2), before
        with expect(migrations.MigrationError, "pending: 0001, 0002"):
            migrations.require_current(conn, root)

        assert migrations.apply_pending(conn, root) == [1, 2]
        assert conn.executed_scripts == ["SELECT 'one';", "SELECT 'two';"]
        assert migrations.apply_pending(conn, root) == []
        after = migrations.status(conn, root)
        assert after.applied == (1, 2) and after.pending == (), after
        migrations.require_current(conn, root)

        first.write_text("SELECT 'da sua';", encoding="utf-8")
        with expect(migrations.MigrationError, "checksum khong khop version 0001"):
            migrations.status(conn, root)
    print("[PASS] status/apply/current va checksum guard dung")


def test_status_chan_migration_da_apply_bi_xoa():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        migration = root / "0001_first.sql"
        migration.write_text("SELECT 1;", encoding="utf-8")
        conn = FakeConnection()
        migrations.apply_pending(conn, root)
        migration.unlink()

        with expect(migrations.MigrationError, "da apply nhung thieu file version 0001"):
            migrations.status(conn, root)
    print("[PASS] status chan migration da apply bi xoa")


def test_apply_rollback_script_va_history_cung_transaction():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
        (root / "0002_broken.sql").write_text("RAISE_FAKE;", encoding="utf-8")
        conn = FakeConnection()

        with expect(RuntimeError, "migration script that bai"):
            migrations.apply_pending(conn, root)

        assert tuple(conn.history) == (1,), conn.history
        assert conn.executed_scripts == ["SELECT 1;"], conn.executed_scripts
    print("[PASS] apply rollback SQL va history cua migration loi")


def test_open_connection_dong_dung_mot_connection():
    calls = []

    class OpenedConnection:
        closed = False

        def close(self):
            self.closed = True

    original_connect = database.psycopg.connect
    original_dsn = database.db.dsn

    def fake_connect(dsn_value, *, autocommit):
        conn = OpenedConnection()
        calls.append((dsn_value, autocommit, conn))
        return conn

    database.psycopg.connect = fake_connect
    database.db.dsn = lambda: "postgresql://default"
    try:
        with database.open_connection() as first:
            assert first.closed is False
        with database.open_connection("postgresql://explicit") as second:
            assert second.closed is False
    finally:
        database.psycopg.connect = original_connect
        database.db.dsn = original_dsn

    assert [(dsn, autocommit) for dsn, autocommit, _ in calls] == [
        ("postgresql://default", True),
        ("postgresql://explicit", True),
    ]
    assert all(conn.closed for _, _, conn in calls)
    print("[PASS] open_connection dung DSN va luon dong connection")


def test_package_khong_che_module_platform_cua_python():
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "import platform; assert hasattr(platform, 'python_implementation'); "
        "from review_platform import migrations; assert migrations.MigrationError"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    print("[PASS] package moi khong che module platform cua Python")


def _reset_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_migration_")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}, public")


def _drop_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_migration_")
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def _scalar(conn, query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    return None if row is None else row[0]


def _snapshot_sha256(relative_path: str) -> str:
    """Bam Git blob da khoa, khong bam checkout bi autocrlf doi bytes."""
    content = subprocess.check_output(
        ["git", "show", f"04f10e1:{relative_path}"],
        cwd=PROJECT_ROOT,
    )
    return hashlib.sha256(content).hexdigest()


def _create_legacy_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            "CREATE TABLE review_job ("
            "id bigserial PRIMARY KEY, node_id text NOT NULL, "
            "content_hash text NOT NULL, status text NOT NULL, "
            "attempts int NOT NULL DEFAULT 0, "
            "run_after timestamptz NOT NULL DEFAULT now(), claimed_at timestamptz, "
            "claimed_by text, last_error text, source text NOT NULL, "
            "created_at timestamptz NOT NULL DEFAULT now(), "
            "updated_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute(
            "CREATE UNIQUE INDEX review_job_dedup ON review_job (node_id, content_hash) "
            "WHERE status IN ('queued', 'running', 'done')"
        )
        cur.execute(
            "CREATE TABLE run_log ("
            "id bigserial PRIMARY KEY, job_id bigint, node_id text NOT NULL, "
            "content_hash text NOT NULL, scored_at timestamptz NOT NULL DEFAULT now(), "
            "duration_ms int, decision text, final_score numeric, "
            "missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb, veto_reason text, "
            "note text, agent_results jsonb NOT NULL, config_meta jsonb NOT NULL, "
            "usage jsonb NOT NULL, model text NOT NULL, payload jsonb NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE kb_chunk (collection text NOT NULL, chunk_id text NOT NULL, "
            "document text NOT NULL, embedding vector(1024) NOT NULL, "
            "content_type text NOT NULL, langcode text NOT NULL, "
            "meta jsonb NOT NULL DEFAULT '{}'::jsonb, "
            "PRIMARY KEY (collection, chunk_id))"
        )
        cur.execute(
            "INSERT INTO review_job (node_id, content_hash, status, source) "
            "VALUES ('legacy-node', 'legacy-hash', 'queued', 'event') RETURNING id"
        )
        job_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO run_log (job_id, node_id, content_hash, duration_ms, decision, "
            "final_score, agent_results, config_meta, usage, model, payload) "
            "VALUES (%s, 'legacy-node', 'legacy-hash', 123, 'needs_revision', 72, "
            "'{}'::jsonb, '{}'::jsonb, '[]'::jsonb, 'legacy-model', %s::jsonb)",
            (job_id, json.dumps({"status": "needs_revision"})),
        )


def test_migration_0001_nang_legacy_bao_toan_du_lieu(conn):
    schema = "vf_test_migration_legacy"
    _reset_schema(conn, schema)
    try:
        _create_legacy_schema(conn)
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == [1, 2, 3, 4, 5]

        assert _scalar(conn, "SELECT count(*) FROM review_job") == 1
        assert _scalar(conn, "SELECT count(*) FROM run_log") == 1
        assert str(_scalar(conn, "SELECT site_id FROM review_job")) == DEFAULT_SITE_ID
        assert str(_scalar(conn, "SELECT profile_id FROM run_log")) == DEFAULT_PROFILE_ID
        assert _scalar(conn, "SELECT external_content_id FROM review_job") == "legacy-node"
        assert _scalar(conn, "SELECT node_id FROM review_job") == "legacy-node"
        assert _scalar(conn, "SELECT payload->>'status' FROM run_log") == "needs_revision"
        assert _scalar(conn, "SELECT writeback_status FROM run_log") == "unknown"
        assert _scalar(
            conn,
            "SELECT count(*) FROM review_job WHERE public_id IS NULL OR site_id IS NULL "
            "OR profile_id IS NULL OR policy_version IS NULL "
            "OR external_content_id IS NULL OR content_type IS NULL "
            "OR langcode IS NULL OR correlation_id IS NULL",
        ) == 0
        assert _scalar(
            conn,
            "SELECT count(*) FROM run_log WHERE public_id IS NULL OR site_id IS NULL "
            "OR profile_id IS NULL OR policy_version IS NULL "
            "OR external_content_id IS NULL OR content_type IS NULL "
            "OR langcode IS NULL OR correlation_id IS NULL OR writeback_status IS NULL",
        ) == 0
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == []
    finally:
        _drop_schema(conn, schema)
    print("[PASS] migration 0001 backfill legacy va bao toan job/run payload")


def test_migration_0001_tao_fresh_schema_va_seed(conn):
    schema = "vf_test_migration_fresh"
    _reset_schema(conn, schema)
    try:
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == [1, 2, 3, 4, 5]
        assert _scalar(conn, "SELECT count(*) FROM site") == 1
        assert _scalar(conn, "SELECT count(*) FROM review_profile") == 1
        assert _scalar(conn, "SELECT count(*) FROM site_profile_assignment") == 1
        assert _scalar(conn, "SELECT slug FROM site") == "drupal-vn-primary"
        assert _scalar(conn, "SELECT code FROM review_profile") == "cam-nang-vn"
        assert _scalar(conn, "SELECT count(*) FROM review_job") == 0
        assert _scalar(conn, "SELECT count(*) FROM run_log") == 0
        assert migrations.status(conn, MIGRATIONS_DIR).pending == ()
    finally:
        _drop_schema(conn, schema)
    print("[PASS] migration 0001 tao fresh schema va seed dung mot scope")


def test_assignment_scope_guard_chan_insert_va_profile_update(conn):
    schema = "vf_test_migration_scope_guard"
    _reset_schema(conn, schema)
    try:
        migrations.apply_pending(conn, MIGRATIONS_DIR)
        second_id = "00000000-0000-4000-8000-000000000003"
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO review_profile "
                "(id, code, market_code, language_code, content_type, status, "
                "policy_version, policy_snapshot) "
                "VALUES (%s, 'second', 'VN', 'vi', 'cam_nang', 'active', "
                "'second-v1', '{}'::jsonb)",
                (second_id,),
            )
        with expect(db.psycopg.errors.UniqueViolation, "active profile trung scope"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO site_profile_assignment (site_id, profile_id) "
                    "VALUES (%s, %s)",
                    (DEFAULT_SITE_ID, second_id),
                )

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE review_profile SET content_type='landing_page' WHERE id=%s",
                (second_id,),
            )
            cur.execute(
                "INSERT INTO site_profile_assignment (site_id, profile_id) VALUES (%s, %s)",
                (DEFAULT_SITE_ID, second_id),
            )
        with expect(db.psycopg.errors.UniqueViolation, "active profile trung scope"):
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE review_profile SET content_type='cam_nang' WHERE id=%s",
                    (second_id,),
                )
    finally:
        _drop_schema(conn, schema)
    print("[PASS] DB chan scope trung khi assign va khi sua profile")


def test_policy_snapshot_khop_hash_nguon_khoa(conn):
    schema = "vf_test_migration_policy"
    _reset_schema(conn, schema)
    try:
        migrations.apply_pending(conn, MIGRATIONS_DIR)
        snapshot = _scalar(conn, "SELECT policy_snapshot FROM review_profile")
        expected_files = {
            "scoring_sha256": "multiagent/config/scoring.yaml",
            "compliance_rules_sha256": "multiagent/src/agents/compliance_rules.json",
            "brand_rules_sha256": "multiagent/src/agents/brand_rules.json",
            "factcheck_kb_specs_sha256": "multiagent/src/kb/specs.json",
            "brand_guideline_sha256": "docs/brand/brand_guideline.md",
            "brand_corpus_index_sha256": "docs/brand/corpus_index.csv",
        }
        for key, path in expected_files.items():
            assert snapshot[key] == _snapshot_sha256(path), (key, path)
        assert snapshot["release"] == "cam-nang-vn-v1"
        assert snapshot["score_path_snapshot"] == "04f10e1"
        assert snapshot["prompt_version"] == "020738e209017213"
        assert snapshot["embedding_dimension"] == 1024
    finally:
        _drop_schema(conn, schema)
    print("[PASS] policy snapshot khop hash tung nguon da khoa")


def test_migration_0001_checksum_guard_tren_database(conn):
    schema = "vf_test_migration_checksum"
    _reset_schema(conn, schema)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            copied_dir = Path(tmp)
            copied = copied_dir / "0001_platform_foundation.sql"
            shutil.copy2(MIGRATIONS_DIR / copied.name, copied)
            migrations.apply_pending(conn, copied_dir)
            copied.write_bytes(copied.read_bytes() + b"\n-- changed after apply\n")
            with expect(migrations.MigrationError, "checksum khong khop version 0001"):
                migrations.status(conn, copied_dir)
    finally:
        _drop_schema(conn, schema)
    print("[PASS] database checksum guard chan sua migration da apply")


def test_migration_0002_tao_schema_admin_auth_va_rang_buoc(conn):
    schema = "vf_test_migration_admin_auth"
    _reset_schema(conn, schema)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            first_only = Path(tmp)
            shutil.copy2(
                MIGRATIONS_DIR / "0001_platform_foundation.sql",
                first_only / "0001_platform_foundation.sql",
            )
            assert migrations.apply_pending(conn, first_only) == [1]

        before = migrations.status(conn, MIGRATIONS_DIR)
        assert before.applied == (1,) and before.pending == (2, 3, 4, 5), before
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == [2, 3, 4, 5]

        expected_tables = {
            "admin_user",
            "admin_session",
            "admin_login_throttle",
            "admin_audit_log",
        }
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname=current_schema() AND tablename LIKE 'admin_%'"
            )
            assert {row[0] for row in cur.fetchall()} == expected_tables
            cur.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=current_schema() "
                "AND indexname='admin_session_active_token_idx'"
            )
            index_definition = cur.fetchone()[0].lower()
            cur.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname=current_schema() "
                "AND indexname='admin_session_user_idx'"
            )
            user_index_row = cur.fetchone()
        assert "token_hash" in index_definition
        assert "where (revoked_at is null)" in index_definition
        assert user_index_row is not None
        assert "(user_id)" in user_index_row[0].lower()

        with expect(db.psycopg.errors.CheckViolation, "admin_user_role_check"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO admin_user "
                    "(username, username_normalized, password_hash, role) "
                    "VALUES ('owner', 'owner', 'hash', 'owner')"
                )

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO admin_user "
                "(username, username_normalized, password_hash, role) "
                "VALUES ('Alice', 'alice', 'hash', 'viewer')"
            )
        with expect(
            db.psycopg.errors.UniqueViolation,
            "admin_user_username_normalized_key",
        ):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO admin_user "
                    "(username, username_normalized, password_hash, role) "
                    "VALUES ('ALICE', 'alice', 'hash-2', 'operator')"
                )
    finally:
        _drop_schema(conn, schema)
    print("[PASS] migration 0002/0003 tao schema, rang buoc va index admin auth")


def test_migration_0004_tao_credential_va_hash_version(conn):
    schema = "vf_test_migration_api_connector"
    _reset_schema(conn, schema)
    try:
        _create_legacy_schema(conn)
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == [1, 2, 3, 4, 5]

        # Row legacy giu version 1: khong duoc rewrite hash lich su thanh v2.
        assert _scalar(conn, "SELECT content_hash_version FROM review_job") == 1
        assert _scalar(conn, "SELECT content_hash_version FROM run_log") == 1
        assert _scalar(conn, "SELECT is_fixture FROM run_log") is False
        assert _scalar(conn, "SELECT source_url FROM run_log") is None

        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name='site_api_credential' "
                "ORDER BY column_name"
            )
            columns = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
        assert set(columns) == {
            "id", "site_id", "token_prefix", "token_hash", "active",
            "created_at", "last_used_at", "revoked_at",
        }, columns
        assert columns["token_hash"][0] == "character", columns["token_hash"]
        assert columns["last_used_at"][1] == "YES", columns["last_used_at"]

        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexdef FROM pg_indexes WHERE schemaname=current_schema() "
                "AND indexname='site_api_credential_prefix'"
            )
            prefix_index = cur.fetchone()
        assert prefix_index is not None, "thieu index prefix"
        assert "where (active" in prefix_index[0].lower(), prefix_index[0]

        # token_hash duy nhat tren toan bang: hai site khong duoc trung token.
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
                "VALUES (%s, 'abc123def456', %s)",
                (DEFAULT_SITE_ID, "a" * 64),
            )
        with expect(db.psycopg.errors.UniqueViolation, "token_hash"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
                    "VALUES (%s, 'khac-prefix', %s)",
                    (DEFAULT_SITE_ID, "a" * 64),
                )

        # Hash version chi duoc phep 1 hoac 2.
        with expect(db.psycopg.errors.CheckViolation, "content_hash_version"):
            with conn.cursor() as cur:
                cur.execute("UPDATE review_job SET content_hash_version=3")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name='site' "
                "AND column_name LIKE 'last_health%'"
            )
            health_columns = {row[0] for row in cur.fetchall()}
        assert health_columns == {
            "last_health_status", "last_health_checked_at", "last_health_error",
        }, health_columns

        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == []
    finally:
        _drop_schema(conn, schema)
    print("[PASS] migration 0004 tao credential, hash version va cot health")


def test_migration_0005_tao_heartbeat_va_usage_event(conn):
    schema = "vf_test_migration_observability"
    _reset_schema(conn, schema)
    try:
        _create_legacy_schema(conn)
        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == [1, 2, 3, 4, 5]

        # Du lieu legacy phai con nguyen sau khi them hai bang moi.
        assert _scalar(conn, "SELECT count(*) FROM review_job") == 1
        assert _scalar(conn, "SELECT count(*) FROM run_log") == 1
        assert _scalar(conn, "SELECT payload->>'status' FROM run_log") == "needs_revision"

        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name='worker_heartbeat'"
            )
            heartbeat_cols = {row[0] for row in cur.fetchall()}
        assert heartbeat_cols == {
            "instance_id", "started_at", "last_seen_at", "version", "current_job_id",
        }, heartbeat_cols

        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name='llm_usage_event'"
            )
            usage_cols = {row[0] for row in cur.fetchall()}
        assert usage_cols == {
            "id", "job_id", "attempt", "sequence_no", "correlation_id", "agent",
            "phase", "model", "input_tokens", "output_tokens", "is_fixture",
            "recorded_at",
        }, usage_cols
        # Tuyet doi khong co cot nao chua prompt/output/noi dung bai.
        assert not (usage_cols & {"prompt", "output", "body", "content", "payload"})

        with expect(db.psycopg.errors.CheckViolation, "instance_len"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO worker_heartbeat "
                    "(instance_id, started_at, last_seen_at, version) "
                    "VALUES ('', now(), now(), 'v1')"
                )

        job_id = _scalar(conn, "SELECT id FROM review_job LIMIT 1")
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO llm_usage_event (job_id, attempt, sequence_no, "
                "correlation_id, agent, phase, model, input_tokens, output_tokens) "
                "VALUES (%s, 1, 1, gen_random_uuid(), 'seo', 'main', 'm', 10, 5)",
                (job_id,),
            )
        # Ghi lai cung (job, attempt, sequence) phai bi chan: khong cong doi chi phi.
        with expect(db.psycopg.errors.UniqueViolation, "llm_usage_event"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO llm_usage_event (job_id, attempt, sequence_no, "
                    "correlation_id, agent, phase, model, input_tokens, output_tokens) "
                    "VALUES (%s, 1, 1, gen_random_uuid(), 'seo', 'main', 'm', 99, 99)",
                    (job_id,),
                )
        with expect(db.psycopg.errors.CheckViolation, "input_tokens"):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO llm_usage_event (job_id, attempt, sequence_no, "
                    "correlation_id, agent, phase, model, input_tokens, output_tokens) "
                    "VALUES (%s, 1, 2, gen_random_uuid(), 'seo', 'main', 'm', -1, 0)",
                    (job_id,),
                )

        assert migrations.apply_pending(conn, MIGRATIONS_DIR) == []
    finally:
        _drop_schema(conn, schema)
    print("[PASS] migration 0005 tao heartbeat/usage event, giu du lieu cu")


if __name__ == "__main__":
    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        postgres_conn = None
        print(
            f"[SKIP] integration migration khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )

    failed = False
    for fn in (
        test_discover_sap_xep_va_checksum_canonical,
        test_discover_checksum_khong_phu_thuoc_lf_hay_crlf,
        test_status_chap_nhan_checksum_crlf_lich_su_nhung_van_chan_sua_sql,
        test_discover_chan_version_trung,
        test_discover_chan_ten_file_sql_sai_quy_uoc,
        test_discover_chan_khoang_trong_version,
        test_status_apply_require_current_va_checksum_guard,
        test_status_chan_migration_da_apply_bi_xoa,
        test_apply_rollback_script_va_history_cung_transaction,
        test_open_connection_dong_dung_mot_connection,
        test_package_khong_che_module_platform_cua_python,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    if postgres_conn is not None:
        for fn in (
            test_migration_0001_nang_legacy_bao_toan_du_lieu,
            test_migration_0001_tao_fresh_schema_va_seed,
            test_assignment_scope_guard_chan_insert_va_profile_update,
            test_policy_snapshot_khop_hash_nguon_khoa,
            test_migration_0001_checksum_guard_tren_database,
            test_migration_0002_tao_schema_admin_auth_va_rang_buoc,
            test_migration_0004_tao_credential_va_hash_version,
            test_migration_0005_tao_heartbeat_va_usage_event,
        ):
            try:
                fn(postgres_conn)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
        postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
