"""End-to-end gia lap toan he: API -> queue -> worker -> callback (Plan 5 Task 5).

Dung API router THAT, PostgreSQL THAT va worker THAT. Chi Drupal va engine LLM
la fake. KHONG goi mang, KHONG goi Anthropic, chi phi $0.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_end_to_end.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import job_queue as q
from _platform_harness import (
    CANARY,
    HASH_V2,
    ConnectorGia,
    EngineGia,
    co_postgres,
    moi_truong,
)


def test_duong_thanh_cong_di_het_mot_vong():
    with moi_truong("vf_test_e2e_happy") as mt:
        tao = mt.post_job()
        assert tao.status_code == 202, tao.text
        than = tao.json()
        assert than["status"] == "queued" and than["duplicate"] is False
        job_public_id = than["job_id"]

        # Job trung tra CUNG job, khong tao them.
        trung = mt.post_job()
        assert trung.status_code == 200, trung.text
        assert trung.json()["job_id"] == job_public_id
        assert mt.scalar("SELECT count(*) FROM review_job") == 1

        ket = mt.chay()
        assert ket["ket"] == q.DONE, ket["ket"]
        assert len(ket["engine"].calls) == 1, "engine phai duoc goi dung mot lan"
        assert len(ket["connector"].fetch_calls) == 1, "fetch dung mot lan"
        assert len(ket["connector"].write_calls) == 1, "callback dung mot lan"

        # Scope phai xuyen suot job -> run.
        job_row = mt.rows(
            "SELECT site_id, profile_id, policy_version, external_revision_id, "
            "content_hash_version, correlation_id, status FROM review_job"
        )[0]
        run_row = mt.rows(
            "SELECT site_id, profile_id, policy_version, external_revision_id, "
            "content_hash_version, correlation_id, writeback_status FROM run_log"
        )[0]
        assert job_row[:6] == run_row[:6], (job_row, run_row)
        assert job_row[6] == "done" and run_row[6] == "succeeded"

        yeu_cau = ket["connector"].write_calls[0]
        assert yeu_cau.content_hash == HASH_V2
        assert yeu_cau.expected_revision_id == "10"
        assert yeu_cau.report_json["platform_run_id"] == str(
            mt.scalar("SELECT public_id FROM run_log")
        )
    print("[PASS] E2E: 202 -> trung 200 -> 1 engine, 1 fetch, 1 callback, scope xuyen suot")


# `test_bao_cao_dang_ngo_van_duoc_escape_khi_render` da bi xoa cung admin
# Jinja2 (2026-08-21). No kiem autoescape cua Jinja2, ma Jinja2 khong con.
# Tinh chat tuong duong cho Console nam o hai cho:
#   - console_ui/src/pages/ReviewDetailPage.test.tsx: chuoi giong the HTML
#     hien ra thanh CHU, khong thanh phan tu
#   - phep grep cam `dangerouslySetInnerHTML` trong ca src/


def test_engine_ghi_usage_roi_loi_van_giu_duoc_chi_phi():
    """Tien da tieu phai vao so ngay ca khi khong bao gio co run_log."""
    from review_platform import usage as platform_usage
    import ai_core

    with moi_truong("vf_test_e2e_usage") as mt:
        mt.post_job()
        job = mt.claim()

        ghi = []
        collector = platform_usage.UsageCollector(sink=lambda **kw: ghi.append(kw))
        goc = ai_core.USAGE_LOG
        ai_core.USAGE_LOG = collector
        try:
            engine = EngineGia(
                usage=[{"model": "m", "input_tokens": 500, "output_tokens": 100}],
                loi=RuntimeError("agent no sau khi tieu tien"),
            )
            ket = mt.chay(job=job, engine=engine)
        finally:
            ai_core.USAGE_LOG = goc

        assert ket["ket"] == q.QUEUED, ket["ket"]
        assert mt.scalar("SELECT count(*) FROM run_log") == 0, "khong co run_log"
        # Nhung usage thi PHAI duoc ghi.
        assert len(ghi) == 1, ghi
        assert ghi[0]["entry"]["input_tokens"] == 500
        assert ghi[0]["job_id"] == job["id"]
    print("[PASS] agent tieu tien roi loi: khong co run_log nhung usage van vao so")


def test_fixture_run_khong_lot_vao_metric_production():
    from review_platform.admin import queries

    with moi_truong("vf_test_e2e_fixture") as mt:
        mt.post_job()
        ket = mt.chay(fixture_run=True)
        assert ket["ket"] == q.DONE

        assert mt.scalar("SELECT count(*) FROM run_log WHERE is_fixture") == 1
        clause = queries._fixture_clause(False)
        assert mt.scalar(f"SELECT count(*) FROM run_log WHERE TRUE {clause}") == 0
    print("[PASS] run fixture bi loai khoi metric production")


def test_khong_luu_toan_van_bai_o_bat_ky_dau():
    with moi_truong("vf_test_e2e_canary") as mt:
        mt.post_job()
        mt.chay()

        for bang in ("review_job", "run_log"):
            noi_dung = str(mt.rows(f"SELECT * FROM {bang}"))
            for ten, chuoi in CANARY.items():
                assert chuoi not in noi_dung, f"{bang} lo canary '{ten}'"
    print("[PASS] khong bang nao luu toan van bai/prompt/secret")


if __name__ == "__main__":
    failed = False

    if not co_postgres():
        print("[SKIP] khong ket noi duoc Postgres; [SKIP] khong phai [PASS]")
        print("OK" if not failed else "CO TEST DO")
        sys.exit(1 if failed else 0)

    for fn in (
        test_duong_thanh_cong_di_het_mot_vong,
        test_engine_ghi_usage_roi_loi_van_giu_duoc_chi_phi,
        test_fixture_run_khong_lot_vao_metric_production,
        test_khong_luu_toan_van_bai_o_bat_ky_dau,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
