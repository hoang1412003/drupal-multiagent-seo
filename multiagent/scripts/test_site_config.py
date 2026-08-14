"""Test cau hinh site theo moi truong: base URL tu env, secret chi la ten.

Seed migration 0001 dat base_url `.ddev.site`. Neu staging/production khoi
dong ma quen buoc nay, connector se goi thang vao Drupal local cua may dev -
day la ly do test bat buoc chung minh URL DDEV bi thay that su.

Chay: .venv\\Scripts\\python.exe scripts\\test_site_config.py
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import db
from review_platform import migrations

import site_config


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def test_chuan_hoa_base_url_bo_dau_gach_cuoi_va_giu_subpath():
    assert site_config.chuan_hoa_base_url(
        "http://drupal.ddev.site/"
    ) == "http://drupal.ddev.site"
    assert site_config.chuan_hoa_base_url(
        "http://drupal.ddev.site"
    ) == "http://drupal.ddev.site"
    assert site_config.chuan_hoa_base_url(
        "https://cms.example.com/drupal/"
    ) == "https://cms.example.com/drupal"
    print("[PASS] chuan hoa base URL bo trailing slash va giu subpath")


def test_chuan_hoa_base_url_tu_choi_url_khong_an_toan():
    for raw, message in (
        ("", "rong"),
        ("drupal.ddev.site", "scheme"),
        ("ftp://drupal.ddev.site", "scheme"),
        ("file:///etc/passwd", "scheme"),
        ("http://", "host"),
        ("https://", "host"),
        ("http://user:matkhau@drupal.ddev.site", "userinfo"),
        ("http://user@drupal.ddev.site", "userinfo"),
        ("http://drupal.ddev.site?debug=1", "query"),
        ("http://drupal.ddev.site#phan", "fragment"),
    ):
        with expect(site_config.SiteConfigError, message):
            site_config.chuan_hoa_base_url(raw)
    print("[PASS] chuan hoa base URL tu choi scheme/host/userinfo/query/fragment sai")


def test_secret_ref_chi_nhan_ten_bien_moi_truong_an_toan():
    assert site_config.chuan_hoa_secret_ref("DRUPAL") == "DRUPAL"
    assert site_config.chuan_hoa_secret_ref("DRUPAL_STAGING_2") == "DRUPAL_STAGING_2"
    for raw in ("", "drupal", "2DRUPAL", "DRUPAL-STAGING", "DRUPAL PASSWORD", "A" * 65):
        with expect(site_config.SiteConfigError, "secret-ref"):
            site_config.chuan_hoa_secret_ref(raw)
    print("[PASS] secret-ref chi nhan ten bien moi truong dang A-Z0-9_")


def _reset_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_site_config_")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def _drop_schema(conn, schema: str) -> None:
    assert schema.startswith("vf_test_site_config_")
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def _scalar(conn, query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    return None if row is None else row[0]


def _run_cli(conn, argv, *, environ=None, printed=None):
    args = site_config.build_parser().parse_args(argv)
    return site_config.execute(
        conn,
        args,
        environ={} if environ is None else environ,
        print_fn=printed.append if printed is not None else (lambda _: None),
    )


def test_set_from_env_thay_that_su_url_ddev_bang_url_staging(conn):
    schema = "vf_test_site_config_staging"
    _reset_schema(conn, schema)
    try:
        assert _scalar(conn, "SELECT base_url FROM site") == "http://drupal.ddev.site"

        _run_cli(
            conn,
            [
                "set-from-env", "--site", "drupal-vn-primary",
                "--base-url-env", "DRUPAL_BASE_URL", "--secret-ref", "DRUPAL_STAGING",
            ],
            environ={"DRUPAL_BASE_URL": "https://staging.example.com/"},
        )

        assert _scalar(conn, "SELECT base_url FROM site") == "https://staging.example.com"
        assert _scalar(conn, "SELECT secret_ref FROM site") == "DRUPAL_STAGING"
    finally:
        _drop_schema(conn, schema)
    print("[PASS] set-from-env thay URL DDEV cua seed bang URL moi truong that")


def test_set_from_env_khong_update_khi_thieu_env_hoac_url_sai(conn):
    schema = "vf_test_site_config_invalid"
    _reset_schema(conn, schema)
    try:
        goc = _scalar(conn, "SELECT base_url FROM site")

        with expect(site_config.SiteConfigError, "DRUPAL_BASE_URL"):
            _run_cli(
                conn,
                [
                    "set-from-env", "--site", "drupal-vn-primary",
                    "--base-url-env", "DRUPAL_BASE_URL", "--secret-ref", "DRUPAL",
                ],
                environ={},
            )
        assert _scalar(conn, "SELECT base_url FROM site") == goc

        with expect(site_config.SiteConfigError, "scheme"):
            _run_cli(
                conn,
                [
                    "set-from-env", "--site", "drupal-vn-primary",
                    "--base-url-env", "DRUPAL_BASE_URL", "--secret-ref", "DRUPAL",
                ],
                environ={"DRUPAL_BASE_URL": "staging.example.com"},
            )
        assert _scalar(conn, "SELECT base_url FROM site") == goc

        with expect(site_config.SiteConfigError, "secret-ref"):
            _run_cli(
                conn,
                [
                    "set-from-env", "--site", "drupal-vn-primary",
                    "--base-url-env", "DRUPAL_BASE_URL", "--secret-ref", "drupal",
                ],
                environ={"DRUPAL_BASE_URL": "https://staging.example.com"},
            )
        assert _scalar(conn, "SELECT base_url FROM site") == goc

        with expect(site_config.SiteConfigError, "site"):
            _run_cli(
                conn,
                [
                    "set-from-env", "--site", "khong-ton-tai",
                    "--base-url-env", "DRUPAL_BASE_URL", "--secret-ref", "DRUPAL",
                ],
                environ={"DRUPAL_BASE_URL": "https://staging.example.com"},
            )
    finally:
        _drop_schema(conn, schema)
    print("[PASS] set-from-env khong ghi DB khi env thieu, URL sai hoac secret-ref sai")


def test_show_chi_in_ten_secret_ref_khong_in_gia_tri(conn):
    schema = "vf_test_site_config_show"
    _reset_schema(conn, schema)
    try:
        printed = []
        _run_cli(
            conn,
            ["show", "--site", "drupal-vn-primary"],
            environ={
                "DRUPAL_USER": "ai_service",
                "DRUPAL_PASSWORD": "matkhau-tuyet-mat",
            },
            printed=printed,
        )

        joined = "\n".join(printed)
        assert "drupal-vn-primary" in joined
        assert "http://drupal.ddev.site" in joined
        assert "DRUPAL" in joined
        assert "matkhau-tuyet-mat" not in joined, joined
        assert "ai_service" not in joined, joined
    finally:
        _drop_schema(conn, schema)
    print("[PASS] show in ten secret-ref nhung khong bao gio in gia tri secret")


if __name__ == "__main__":
    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        postgres_conn = None
        print(
            f"[SKIP] integration site config khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )

    failed = False
    for fn in (
        test_chuan_hoa_base_url_bo_dau_gach_cuoi_va_giu_subpath,
        test_chuan_hoa_base_url_tu_choi_url_khong_an_toan,
        test_secret_ref_chi_nhan_ten_bien_moi_truong_an_toan,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    if postgres_conn is not None:
        for fn in (
            test_set_from_env_thay_that_su_url_ddev_bang_url_staging,
            test_set_from_env_khong_update_khi_thieu_env_hoac_url_sai,
            test_show_chi_in_ten_secret_ref_khong_in_gia_tri,
        ):
            try:
                fn(postgres_conn)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
        postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
