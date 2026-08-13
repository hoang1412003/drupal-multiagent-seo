"""Test migration runner SQL co version va checksum.

Phan discovery chay hoan toan khong can Postgres. Cac integration test schema
se duoc bo sung o Task 2 va phai ghi ro [SKIP] neu DB local chua san sang.

Chay: .venv\\Scripts\\python.exe scripts\\test_migrations.py
"""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from platform import database, migrations


@contextmanager
def expect(exc_type, message: str):
    """Bat dung loai exception va mot doan message, khong can test framework."""
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def test_discover_sap_xep_va_checksum_dung_bytes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "0002_second.sql").write_bytes(b"SELECT 2;\r\n")
        (root / "0001_first.sql").write_bytes(b"SELECT 1;\n")

        found = migrations.discover(root)

        assert [m.version for m in found] == [1, 2], found
        assert [m.name for m in found] == ["first", "second"], found
        assert found[0].checksum == hashlib.sha256(b"SELECT 1;\n").hexdigest()
        assert found[1].checksum == hashlib.sha256(b"SELECT 2;\r\n").hexdigest()
    print("[PASS] discover sap xep version va bam dung bytes tren disk")


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


if __name__ == "__main__":
    failed = False
    for fn in (
        test_discover_sap_xep_va_checksum_dung_bytes,
        test_discover_chan_version_trung,
        test_discover_chan_ten_file_sql_sai_quy_uoc,
        test_discover_chan_khoang_trong_version,
        test_status_apply_require_current_va_checksum_guard,
        test_status_chan_migration_da_apply_bi_xoa,
        test_apply_rollback_script_va_history_cung_transaction,
        test_open_connection_dong_dung_mot_connection,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
