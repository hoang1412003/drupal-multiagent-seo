"""Integration test chon site/review profile dung scope, khong fallback.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_context.py
"""
import os
from pathlib import Path
import sys
from contextlib import contextmanager
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
from review_platform import migrations, sites


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SCHEMA = "vf_test_platform_context"
DEFAULT_SITE_ID = UUID("00000000-0000-4000-8000-000000000001")


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


def _reset_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)


def test_load_site_by_slug_tra_day_du_context(conn):
    site = sites.load_site_by_slug(conn, "drupal-vn-primary")
    assert site.id == DEFAULT_SITE_ID, site
    assert site.connector_type == "drupal", site
    assert site.base_url == "http://drupal.ddev.site", site
    assert site.secret_ref == "DRUPAL", site
    assert site.active is True and site.intake_paused is False, site
    print("[PASS] load site theo slug tra day du connector context")


def test_select_review_context_dung_scope(conn):
    ctx = sites.select_review_context(conn, DEFAULT_SITE_ID, "cam_nang", "vi")
    assert ctx.site.slug == "drupal-vn-primary", ctx
    assert ctx.profile.code == "cam-nang-vn", ctx
    assert ctx.profile.market_code == "VN", ctx
    assert ctx.profile.language_code == "vi", ctx
    assert ctx.profile.content_type == "cam_nang", ctx
    assert ctx.profile.policy_version == "cam-nang-vn-v1", ctx
    assert ctx.profile.policy_snapshot["score_path_snapshot"] == "04f10e1", ctx
    print("[PASS] select context tra dung site/profile active theo scope")


def test_select_review_context_khong_fallback_khi_thieu(conn):
    with expect(sites.ContextSelectionError, "khong co profile active"):
        sites.select_review_context(conn, DEFAULT_SITE_ID, "landing_page", "vi")
    with expect(sites.ContextSelectionError, "khong co profile active"):
        sites.select_review_context(
            conn,
            UUID("00000000-0000-4000-8000-000000000099"),
            "cam_nang",
            "vi",
        )
    print("[PASS] scope/site khong match thi nem loi, khong fallback")


def test_select_review_context_yeu_cau_ca_ba_lop_active(conn):
    queries = (
        "UPDATE site SET active=false WHERE id=%s",
        "UPDATE site_profile_assignment SET active=false WHERE site_id=%s",
        (
            "UPDATE review_profile SET status='inactive' "
            "WHERE id=(SELECT profile_id FROM site_profile_assignment WHERE site_id=%s)"
        ),
    )
    for query in queries:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_SITE_ID,))
        with expect(sites.ContextSelectionError, "khong co profile active"):
            sites.select_review_context(conn, DEFAULT_SITE_ID, "cam_nang", "vi")
        with conn.cursor() as cur:
            cur.execute("UPDATE site SET active=true WHERE id=%s", (DEFAULT_SITE_ID,))
            cur.execute(
                "UPDATE site_profile_assignment SET active=true WHERE site_id=%s",
                (DEFAULT_SITE_ID,),
            )
            cur.execute(
                "UPDATE review_profile SET status='active' "
                "WHERE id=(SELECT profile_id FROM site_profile_assignment WHERE site_id=%s)",
                (DEFAULT_SITE_ID,),
            )
    print("[PASS] select context yeu cau site/assignment/profile deu active")


def test_select_review_context_chan_du_lieu_trung_du_db_guard_bi_vo_hieu(conn):
    second_profile = UUID("00000000-0000-4000-8000-000000000003")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO review_profile "
            "(id, code, market_code, language_code, content_type, status, "
            "policy_version, policy_snapshot) "
            "VALUES (%s, 'duplicate-context', 'VN', 'vi', 'cam_nang', 'active', "
            "'duplicate-v1', '{}'::jsonb)",
            (second_profile,),
        )
        # Chi trong schema test: mo phong du lieu cu/restore sai da lot qua DB guard
        # de xac minh application van khong che loi bang LIMIT 1.
        cur.execute(
            "ALTER TABLE site_profile_assignment "
            "DISABLE TRIGGER site_profile_assignment_scope_guard"
        )
        cur.execute(
            "INSERT INTO site_profile_assignment (site_id, profile_id) VALUES (%s, %s)",
            (DEFAULT_SITE_ID, second_profile),
        )
        cur.execute(
            "ALTER TABLE site_profile_assignment "
            "ENABLE TRIGGER site_profile_assignment_scope_guard"
        )

    with expect(sites.ContextSelectionError, "co nhieu profile active"):
        sites.select_review_context(conn, DEFAULT_SITE_ID, "cam_nang", "vi")
    print("[PASS] application chan profile trung, khong LIMIT 1 che cau hinh loi")


def test_load_site_by_slug_khong_co_thi_nem_loi(conn):
    with expect(sites.ContextSelectionError, "khong co site"):
        sites.load_site_by_slug(conn, "khong-ton-tai")
    print("[PASS] slug khong ton tai thi nem loi ro rang")


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
        _reset_schema(connection)
        for fn in (
            test_load_site_by_slug_tra_day_du_context,
            test_select_review_context_dung_scope,
            test_select_review_context_khong_fallback_khi_thieu,
            test_select_review_context_yeu_cau_ca_ba_lop_active,
            test_load_site_by_slug_khong_co_thi_nem_loi,
            test_select_review_context_chan_du_lieu_trung_du_db_guard_bi_vo_hieu,
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
