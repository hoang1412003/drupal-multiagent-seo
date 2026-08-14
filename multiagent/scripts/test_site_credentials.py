"""Test credential theo site: parse Bearer, tra cuu hash va CLI quan ly token.

Phan parse chay khong can Postgres. Phan con lai dung schema cach ly va
DROP trong finally; khong ket noi duoc thi in [SKIP], khong phai [PASS].

Chay: .venv\\Scripts\\python.exe scripts\\test_site_credentials.py
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import db
from review_platform import migrations
from review_platform.api import auth

import site_credential


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
DEFAULT_SITE_ID = "00000000-0000-4000-8000-000000000001"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def test_parse_bearer_chi_chap_nhan_dung_mot_scheme_va_token_khong_rong():
    assert auth.parse_bearer("Bearer abc123") == "abc123"

    for header, reason in (
        ("", "missing_authorization"),
        ("   ", "malformed_authorization"),
        ("Bearer", "malformed_authorization"),
        ("Bearer ", "malformed_authorization"),
        ("Bearer  abc", "malformed_authorization"),
        ("Bearer abc def", "malformed_authorization"),
        ("Bearer Bearer abc", "malformed_authorization"),
        ("Basic abc123", "unsupported_scheme"),
        ("bearer abc123", "unsupported_scheme"),
        ("BEARER abc123", "unsupported_scheme"),
    ):
        with expect(auth.CredentialError, reason):
            auth.parse_bearer(header)
    print("[PASS] parse_bearer chan header thieu/sai scheme/token rong")


def test_token_sinh_ra_du_dai_va_prefix_khong_phai_bi_mat():
    token = auth.generate_token()
    assert len(token) >= 40, len(token)
    assert auth.token_prefix(token) == token[:12]
    assert auth.hash_token(token) == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert auth.hash_token(token) != token
    print("[PASS] token sinh du entropy, hash khac raw va prefix la 12 ky tu dau")


def _reset_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_credential_")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _drop_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_credential_")
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def _insert_credential(conn, token: str, *, active: bool = True):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site_api_credential "
            "(site_id, token_prefix, token_hash, active) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (DEFAULT_SITE_ID, auth.token_prefix(token), auth.hash_token(token), active),
        )
        return cur.fetchone()[0]


def _scalar(conn, query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    return None if row is None else row[0]


def test_authenticate_tra_ve_site_principal_dung_site(conn):
    schema = "vf_test_credential_ok"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        credential_id = _insert_credential(conn, token)

        principal = auth.authenticate_bearer(conn, f"Bearer {token}")

        assert str(principal.site.id) == DEFAULT_SITE_ID
        assert principal.site.slug == "drupal-vn-primary"
        assert principal.credential_id == credential_id
        assert principal.token_prefix == auth.token_prefix(token)
        # Raw token khong bao gio duoc luu: tra cuu bang raw phai khong thay gi.
        assert _scalar(
            conn,
            "SELECT count(*) FROM site_api_credential WHERE token_hash=%s",
            (token,),
        ) == 0
    finally:
        _drop_schema(conn, schema)
    print("[PASS] authenticate tra ve dung site va khong luu raw token")


def test_authenticate_tu_choi_token_sai_revoked_va_site_inactive(conn):
    schema = "vf_test_credential_reject"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        _insert_credential(conn, token)

        with expect(auth.CredentialError, "unknown_token"):
            auth.authenticate_bearer(conn, f"Bearer {token}x")

        # Cung prefix nhung hash khac: phai truot o buoc compare_digest.
        cung_prefix = auth.token_prefix(token) + "z" * 30
        assert auth.token_prefix(cung_prefix) == auth.token_prefix(token)
        with expect(auth.CredentialError, "unknown_token"):
            auth.authenticate_bearer(conn, f"Bearer {cung_prefix}")

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE site_api_credential SET active=false, revoked_at=now()"
            )
        with expect(auth.CredentialError, "unknown_token"):
            auth.authenticate_bearer(conn, f"Bearer {token}")

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE site_api_credential SET active=true, revoked_at=NULL"
            )
            cur.execute("UPDATE site SET active=false")
        with expect(auth.CredentialError, "site_inactive"):
            auth.authenticate_bearer(conn, f"Bearer {token}")

        # Site tam dung intake van xac thuc duoc: 423 la viec cua router.
        with conn.cursor() as cur:
            cur.execute("UPDATE site SET active=true, intake_paused=true")
        principal = auth.authenticate_bearer(conn, f"Bearer {token}")
        assert principal.site.intake_paused is True
    finally:
        _drop_schema(conn, schema)
    print("[PASS] authenticate tu choi token sai/revoked/site inactive, van cho paused")


def test_last_used_at_toi_da_moi_5_phut_mot_lan(conn):
    schema = "vf_test_credential_touch"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        _insert_credential(conn, token)
        assert _scalar(conn, "SELECT last_used_at FROM site_api_credential") is None

        moc = datetime(2026, 8, 14, 10, 0, 0, tzinfo=timezone.utc)
        auth.authenticate_bearer(conn, f"Bearer {token}", now=moc)
        lan_dau = _scalar(conn, "SELECT last_used_at FROM site_api_credential")
        assert lan_dau is not None

        auth.authenticate_bearer(conn, f"Bearer {token}", now=moc + timedelta(minutes=4))
        assert _scalar(conn, "SELECT last_used_at FROM site_api_credential") == lan_dau

        auth.authenticate_bearer(conn, f"Bearer {token}", now=moc + timedelta(minutes=6))
        sau = _scalar(conn, "SELECT last_used_at FROM site_api_credential")
        assert sau > lan_dau, (lan_dau, sau)
    finally:
        _drop_schema(conn, schema)
    print("[PASS] last_used_at chi cap nhat toi da moi 5 phut")


def _run_cli(conn, argv, *, environ=None, printed=None):
    args = site_credential.build_parser().parse_args(argv)
    return site_credential.execute(
        conn,
        args,
        environ={} if environ is None else environ,
        print_fn=printed.append if printed is not None else (lambda _: None),
    )


def test_cli_import_env_khong_in_raw_token(conn):
    schema = "vf_test_credential_import"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        printed = []
        _run_cli(
            conn,
            ["import-env", "--site", "drupal-vn-primary", "--env", "VF_SERVICE_TOKEN"],
            environ={"VF_SERVICE_TOKEN": token},
            printed=printed,
        )

        assert _scalar(conn, "SELECT count(*) FROM site_api_credential") == 1
        assert _scalar(conn, "SELECT token_hash FROM site_api_credential") == (
            auth.hash_token(token)
        )
        assert all(token not in line for line in printed), printed

        with expect(site_credential.CredentialCLIError, "VF_SERVICE_TOKEN"):
            _run_cli(
                conn,
                ["import-env", "--site", "drupal-vn-primary", "--env", "VF_SERVICE_TOKEN"],
                environ={},
            )
    finally:
        _drop_schema(conn, schema)
    print("[PASS] import-env luu hash, khong in raw va bao loi khi thieu env")


def test_cli_rotate_revoke_credential_cu_trong_cung_transaction(conn):
    schema = "vf_test_credential_rotate"
    _reset_schema(conn, schema)
    try:
        cu = auth.generate_token()
        _insert_credential(conn, cu)
        printed = []

        _run_cli(conn, ["rotate", "--site", "drupal-vn-primary"], printed=printed)

        assert _scalar(
            conn, "SELECT count(*) FROM site_api_credential WHERE active"
        ) == 1
        assert _scalar(
            conn,
            "SELECT count(*) FROM site_api_credential "
            "WHERE NOT active AND revoked_at IS NOT NULL",
        ) == 1
        with expect(auth.CredentialError, "unknown_token"):
            auth.authenticate_bearer(conn, f"Bearer {cu}")

        # Plaintext in dung mot lan va xac thuc duoc ngay.
        moi = [line.split()[-1] for line in printed if "token" in line.lower()]
        assert len(moi) == 1, printed
        principal = auth.authenticate_bearer(conn, f"Bearer {moi[0]}")
        assert str(principal.site.id) == DEFAULT_SITE_ID
    finally:
        _drop_schema(conn, schema)
    print("[PASS] rotate revoke token cu, in plaintext dung mot lan va token moi chay duoc")


def test_cli_revoke_tu_choi_bo_site_khong_con_credential_active(conn):
    schema = "vf_test_credential_revoke"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        credential_id = _insert_credential(conn, token)

        with expect(site_credential.CredentialCLIError, "allow-no-active"):
            _run_cli(conn, ["revoke", "--credential", str(credential_id)])
        assert _scalar(
            conn, "SELECT count(*) FROM site_api_credential WHERE active"
        ) == 1

        _run_cli(
            conn,
            ["revoke", "--credential", str(credential_id), "--allow-no-active"],
        )
        assert _scalar(
            conn, "SELECT count(*) FROM site_api_credential WHERE active"
        ) == 0
    finally:
        _drop_schema(conn, schema)
    print("[PASS] revoke chan bo credential active cuoi cung tru khi co co y")


def test_cli_list_chi_in_prefix_va_trang_thai(conn):
    schema = "vf_test_credential_list"
    _reset_schema(conn, schema)
    try:
        token = auth.generate_token()
        _insert_credential(conn, token)
        printed = []

        _run_cli(conn, ["list", "--site", "drupal-vn-primary"], printed=printed)

        joined = "\n".join(printed)
        assert auth.token_prefix(token) in joined, joined
        assert token not in joined
        assert auth.hash_token(token) not in joined
        assert "active" in joined.lower()
    finally:
        _drop_schema(conn, schema)
    print("[PASS] list chi in prefix/trang thai, khong lo raw token hay hash")


if __name__ == "__main__":
    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        postgres_conn = None
        print(
            f"[SKIP] integration credential khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )

    failed = False
    for fn in (
        test_parse_bearer_chi_chap_nhan_dung_mot_scheme_va_token_khong_rong,
        test_token_sinh_ra_du_dai_va_prefix_khong_phai_bi_mat,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    if postgres_conn is not None:
        for fn in (
            test_authenticate_tra_ve_site_principal_dung_site,
            test_authenticate_tu_choi_token_sai_revoked_va_site_inactive,
            test_last_used_at_toi_da_moi_5_phut_mot_lan,
            test_cli_import_env_khong_in_raw_token,
            test_cli_rotate_revoke_credential_cu_trong_cung_transaction,
            test_cli_revoke_tu_choi_bo_site_khong_con_credential_active,
            test_cli_list_chi_in_prefix_va_trang_thai,
        ):
            try:
                fn(postgres_conn)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
        postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
