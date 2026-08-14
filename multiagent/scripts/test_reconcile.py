"""Test vong doi soat theo site (spec 2026-08-07 muc 6.3; Plan 4 Task 6).

Chay offline hoan toan: site loader, connector va queue deu tiem duoc.
Phan integration dung Postgres that de chung minh site paused/inactive bi loai
o dung tang SQL chu khong phai chi o Python.

Chay: .venv\\Scripts\\python.exe scripts\\test_reconcile.py
"""
import os
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
import job_queue as q
import reconcile
from review_platform import migrations
from review_platform.connectors import base as connector_base

SCHEMA = "vf_test_reconcile"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SITE_A = UUID("00000000-0000-4000-8000-000000000001")
SITE_B = UUID("00000000-0000-4000-8000-0000000000b1")
SITE_C = UUID("00000000-0000-4000-8000-0000000000c1")


def _item(external_content_id, *, revision="10", content_hash=None, langcode="vi",
          content_type="cam_nang", version=2):
    return connector_base.PendingContent(
        external_content_id=external_content_id,
        external_revision_id=revision,
        content_hash=content_hash or ("a" * 64),
        content_type=content_type,
        langcode=langcode,
        source_url=None,
        content_hash_version=version,
    )


class ConnectorGia:
    def __init__(self, *trang, loi=None):
        self.trang = list(trang) or [connector_base.PendingPage()]
        self.loi = loi
        self.calls = []

    def list_pending(self, *, after_revision_id=0, limit=50):
        self.calls.append({"after": after_revision_id, "limit": limit})
        if self.loi is not None:
            raise self.loi
        if not self.trang:
            return connector_base.PendingPage()
        return self.trang.pop(0)


class ContextGia:
    def __init__(self, site_id, policy_version="cam-nang-vn-v1"):
        self.site = type("S", (), {"id": site_id})()
        self.profile = type("P", (), {"policy_version": policy_version})()


def _quet(conn, *, sites_list, connectors, enqueue_ket_qua=None, that_bai=()):
    xep = []

    def enqueue_fn(_conn, context, external_content_id, content_hash, source, **kw):
        xep.append({
            "site_id": context.site.id,
            "external_content_id": external_content_id,
            "content_hash": content_hash,
            "source": source,
            **kw,
        })
        if enqueue_ket_qua is not None:
            return enqueue_ket_qua
        return {"status": q.QUEUED, "job_id": len(xep), "public_id": None}

    def co_that_bai(_conn, *, site_id, external_content_id, content_hash,
                    policy_version):
        return external_content_id in that_bai

    goc = reconcile.sites.select_review_context
    reconcile.sites.select_review_context = (
        lambda _conn, site_id, content_type, langcode: ContextGia(site_id)
    )
    try:
        tom_tat = reconcile.quet(
            conn,
            site_loader=lambda _conn: sites_list,
            connector_factory=lambda _conn, site_id: connectors[site_id],
            enqueue_fn=enqueue_fn,
            co_that_bai=co_that_bai,
        )
    finally:
        reconcile.sites.select_review_context = goc
    return tom_tat, xep


def test_moi_site_duoc_quet_bang_connector_cua_chinh_no():
    connectors = {
        SITE_A: ConnectorGia(connector_base.PendingPage(items=(_item("a-1"),))),
        SITE_B: ConnectorGia(connector_base.PendingPage(items=(_item("b-1"),))),
    }
    tom_tat, xep = _quet(None, sites_list=[SITE_A, SITE_B], connectors=connectors)

    assert tom_tat.sites_scanned == 2, tom_tat
    assert tom_tat.enqueued == 2, tom_tat
    assert [row["site_id"] for row in xep] == [SITE_A, SITE_B], xep
    assert all(row["source"] == "reconcile" for row in xep), xep
    print("[PASS] moi site duoc quet bang connector cua chinh no")


def test_enqueue_mang_revision_va_hash_version_tu_feed():
    connectors = {
        SITE_A: ConnectorGia(
            connector_base.PendingPage(items=(_item("a-1", revision="42"),))
        )
    }
    _, xep = _quet(None, sites_list=[SITE_A], connectors=connectors)

    assert xep[0]["external_revision_id"] == "42", xep
    assert xep[0]["content_hash_version"] == 2, xep
    print("[PASS] enqueue mang dung revision ID va hash version tu feed")


def test_item_legacy_khong_co_revision_van_xep_duoc():
    """Feed legacy khong co revision -> worker se fetch working copy."""
    connectors = {
        SITE_A: ConnectorGia(
            connector_base.PendingPage(
                items=(_item("a-legacy", revision=None, version=1),)
            )
        )
    }
    _, xep = _quet(None, sites_list=[SITE_A], connectors=connectors)

    assert xep[0]["external_revision_id"] is None, xep
    assert xep[0]["content_hash_version"] == 1, xep
    print("[PASS] item legacy khong co revision van xep duoc voi hash version 1")


def test_dead_letter_dung_scope_khong_bi_hoi_sinh():
    connectors = {
        SITE_A: ConnectorGia(
            connector_base.PendingPage(items=(_item("a-1"), _item("a-2")))
        )
    }
    tom_tat, xep = _quet(
        None, sites_list=[SITE_A], connectors=connectors, that_bai={"a-1"}
    )

    assert [row["external_content_id"] for row in xep] == ["a-2"], xep
    assert tom_tat.skipped_dead_letter == 1, tom_tat
    assert tom_tat.enqueued == 1, tom_tat
    print("[PASS] job da dead-letter khong bi vong doi soat hoi sinh")


def test_mot_site_loi_khong_lam_bo_qua_site_sau():
    connectors = {
        SITE_A: ConnectorGia(loi=connector_base.ConnectorAuthError("403")),
        SITE_B: ConnectorGia(connector_base.PendingPage(items=(_item("b-1"),))),
    }
    tom_tat, xep = _quet(None, sites_list=[SITE_A, SITE_B], connectors=connectors)

    assert [row["external_content_id"] for row in xep] == ["b-1"], xep
    assert tom_tat.enqueued == 1, tom_tat
    assert tom_tat.errors == ((str(SITE_A), "ConnectorAuthError"),), tom_tat
    print("[PASS] mot site loi khong lam bo qua cac site con lai")


def test_phan_trang_chay_den_khi_het_cursor():
    connectors = {
        SITE_A: ConnectorGia(
            connector_base.PendingPage(
                items=(_item("a-1"),), next_after_revision_id=10
            ),
            connector_base.PendingPage(
                items=(_item("a-2"),), next_after_revision_id=20
            ),
            connector_base.PendingPage(items=(_item("a-3"),)),
        )
    }
    tom_tat, xep = _quet(None, sites_list=[SITE_A], connectors=connectors)

    assert tom_tat.enqueued == 3, tom_tat
    assert [call["after"] for call in connectors[SITE_A].calls] == [0, 10, 20]
    assert all(call["limit"] == 50 for call in connectors[SITE_A].calls)
    print("[PASS] phan trang di het cursor, moi trang toi da 50 item")


def test_khong_co_profile_khop_thi_bo_qua_chu_khong_dung_mac_dinh():
    connectors = {
        SITE_A: ConnectorGia(
            connector_base.PendingPage(
                items=(_item("a-1", langcode="en"), _item("a-2"))
            )
        )
    }
    xep = []

    def enqueue_fn(_conn, context, external_content_id, *a, **kw):
        xep.append(external_content_id)
        return {"status": q.QUEUED}

    def chon_context(_conn, site_id, content_type, langcode):
        if langcode != "vi":
            raise reconcile.sites.ContextSelectionError("khong co profile active")
        return ContextGia(site_id)

    goc = reconcile.sites.select_review_context
    reconcile.sites.select_review_context = chon_context
    try:
        tom_tat = reconcile.quet(
            None,
            site_loader=lambda _conn: [SITE_A],
            connector_factory=lambda _conn, site_id: connectors[site_id],
            enqueue_fn=enqueue_fn,
            co_that_bai=lambda *a, **kw: False,
        )
    finally:
        reconcile.sites.select_review_context = goc

    assert xep == ["a-2"], xep
    assert tom_tat.enqueued == 1, tom_tat
    print("[PASS] item khong co profile khop bi bo qua, khong roi ve mac dinh")


def test_summary_truthy_theo_so_job_da_xep():
    assert not reconcile.ReconcileSummary(sites_scanned=3)
    assert reconcile.ReconcileSummary(enqueued=1)
    print("[PASS] ReconcileSummary truthy dung theo so job da xep them")


# -------------------------------------------------------------- integration


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    migrations.apply_pending(conn, MIGRATIONS_DIR)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site (id, slug, name, connector_type, base_url, "
            "secret_ref, active, intake_paused) VALUES "
            "(%s,'site-paused','B','drupal','http://b.test','DRUPAL',true,true),"
            "(%s,'site-inactive','C','drupal','http://c.test','DRUPAL',false,false)",
            (SITE_B, SITE_C),
        )


def test_site_paused_va_inactive_bi_loai_ngay_o_tang_sql(conn):
    _reset_schema(conn)
    try:
        can_quet = reconcile._sites_can_quet(conn)
        assert can_quet == [SITE_A], can_quet

        # Bo tam dung -> site B duoc quet tro lai; site C tat van bi loai.
        with conn.cursor() as cur:
            cur.execute("UPDATE site SET intake_paused=false WHERE id=%s", (SITE_B,))
        assert set(reconcile._sites_can_quet(conn)) == {SITE_A, SITE_B}
    finally:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("[PASS] site tam dung va site tat bi loai ngay trong cau SQL chon site")


def test_site_paused_thi_connector_khong_bao_gio_duoc_goi(conn):
    _reset_schema(conn)
    try:
        da_goi = []

        def factory(_conn, site_id):
            da_goi.append(site_id)
            return ConnectorGia()

        reconcile.quet(
            conn,
            connector_factory=factory,
            enqueue_fn=lambda *a, **kw: {"status": q.QUEUED},
            co_that_bai=lambda *a, **kw: False,
        )
        assert SITE_B not in da_goi, da_goi
        assert SITE_C not in da_goi, da_goi
    finally:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("[PASS] site tam dung khong bi cham toi - tam dung that su co hieu luc")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_moi_site_duoc_quet_bang_connector_cua_chinh_no,
        test_enqueue_mang_revision_va_hash_version_tu_feed,
        test_item_legacy_khong_co_revision_van_xep_duoc,
        test_dead_letter_dung_scope_khong_bi_hoi_sinh,
        test_mot_site_loi_khong_lam_bo_qua_site_sau,
        test_phan_trang_chay_den_khi_het_cursor,
        test_khong_co_profile_khop_thi_bo_qua_chu_khong_dung_mac_dinh,
        test_summary_truthy_theo_so_job_da_xep,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    try:
        postgres_conn = db.psycopg.connect(db.dsn(), autocommit=True)
    except Exception as exc:
        postgres_conn = None
        print(
            f"[SKIP] integration reconcile khong ket noi duoc Postgres "
            f"({exc.__class__.__name__}); [SKIP] khong phai [PASS]"
        )
    if postgres_conn is not None:
        for fn in (
            test_site_paused_va_inactive_bi_loai_ngay_o_tang_sql,
            test_site_paused_thi_connector_khong_bao_gio_duoc_goi,
        ):
            try:
                fn(postgres_conn)
            except Exception as exc:
                failed = True
                print(f"[FAIL] {fn.__name__}: {exc}")
        postgres_conn.close()
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
