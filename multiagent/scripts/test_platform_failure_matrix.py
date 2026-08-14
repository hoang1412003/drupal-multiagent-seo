"""Ma tran hong hoc: moi case co trang thai/retry/engine/callback mong doi.

Muc dich khong phai "he thong chay duoc" ma "he thong hong DUNG CACH". Voi
moi kieu hong, ba con so phai dung: co goi LLM khong, co callback khong, va
job ket thuc o trang thai nao.

Hai con so dau lien quan truc tiep den tien va den du lieu cua nguoi dung:
goi LLM thua la tieu tien, callback thua la ghi de bao cao.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_failure_matrix.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import job_queue as q
from _platform_harness import (
    HASH_V1,
    HASH_V2,
    ConnectorGia,
    EngineGia,
    co_postgres,
    moi_truong,
    tai_lieu,
)
from review_platform.connectors import base as connector_base


def _kiem(ten, *, ket, engine, connector, trang_thai, so_engine, so_callback):
    assert ket == trang_thai, f"{ten}: trang thai {ket}, mong doi {trang_thai}"
    assert len(engine.calls) == so_engine, (
        f"{ten}: goi engine {len(engine.calls)} lan, mong doi {so_engine}"
    )
    assert len(connector.write_calls) == so_callback, (
        f"{ten}: callback {len(connector.write_calls)} lan, mong doi {so_callback}"
    )


# ------------------------------------------------ nhom 1: chan tu tang API


def test_site_tam_dung_khong_tao_job_va_khong_goi_gi():
    with moi_truong("vf_test_fm_paused") as mt:
        with mt.conn.cursor() as cur:
            cur.execute("UPDATE site SET intake_paused=true")
        phan_hoi = mt.post_job()
        assert phan_hoi.status_code == 423, phan_hoi.status_code
        assert mt.scalar("SELECT count(*) FROM review_job") == 0
    print("[PASS] site tam dung -> 423, khong job, khong engine, khong callback")


def test_token_sai_hoac_revoked_khong_tao_job():
    with moi_truong("vf_test_fm_token") as mt:
        sai = mt.post_job(_token="token-bia-dat")
        assert sai.status_code == 401, sai.status_code

        with mt.conn.cursor() as cur:
            cur.execute("UPDATE site_api_credential SET active=false")
        thu_hoi = mt.post_job()
        assert thu_hoi.status_code == 401, thu_hoi.status_code
        assert mt.scalar("SELECT count(*) FROM review_job") == 0
    print("[PASS] token sai/revoked -> 401, khong tao job")


def test_khong_co_profile_khop_khong_tao_job():
    with moi_truong("vf_test_fm_profile") as mt:
        phan_hoi = mt.post_job(langcode="en")
        assert phan_hoi.status_code == 422, phan_hoi.status_code
        assert "profile_not_found" in phan_hoi.text
        assert mt.scalar("SELECT count(*) FROM review_job") == 0
    print("[PASS] khong co profile khop -> 422, khong tao job, khong dung mac dinh")


# --------------------------------------- nhom 2: hong truoc khi goi engine


def test_revision_bien_mat_thi_dead_letter_khong_goi_LLM():
    with moi_truong("vf_test_fm_revision") as mt:
        mt.post_job()
        engine = EngineGia()
        connector = ConnectorGia(
            loi_fetch=connector_base.ConnectorRevisionNotFound("404 revision")
        )
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("revision 404", ket=ket["ket"], engine=engine, connector=connector,
              trang_thai=q.FAILED, so_engine=0, so_callback=0)
        assert mt.scalar("SELECT count(*) FROM run_log") == 0
    print("[PASS] revision 404 -> dead-letter ngay, 0 engine, 0 callback")


def test_hash_lech_thi_dead_letter_khong_goi_LLM():
    with moi_truong("vf_test_fm_hash") as mt:
        mt.post_job()
        engine = EngineGia()
        connector = ConnectorGia(doc=tai_lieu(fields={"title": "noi dung khac"}))
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("hash lech", ket=ket["ket"], engine=engine, connector=connector,
              trang_thai=q.FAILED, so_engine=0, so_callback=0)
        assert mt.scalar(
            "SELECT last_error FROM review_job"
        ).startswith("input_hash_mismatch")
    print("[PASS] hash lech -> dead-letter truoc LLM, 0 engine, 0 callback")


def test_connector_timeout_truoc_engine_thi_retry_khong_ton_tien():
    with moi_truong("vf_test_fm_timeout") as mt:
        mt.post_job()
        engine = EngineGia()
        connector = ConnectorGia(
            loi_fetch=connector_base.ConnectorTransientError("timeout")
        )
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("connector timeout", ket=ket["ket"], engine=engine,
              connector=connector, trang_thai=q.QUEUED, so_engine=0, so_callback=0)
    print("[PASS] connector timeout truoc engine -> queued/backoff, khong ton tien")


def test_loi_auth_vao_thang_dead_letter_khong_thu_ba_lan():
    with moi_truong("vf_test_fm_auth") as mt:
        mt.post_job()
        engine = EngineGia()
        connector = ConnectorGia(
            loi_fetch=connector_base.ConnectorAuthError("403")
        )
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("auth", ket=ket["ket"], engine=engine, connector=connector,
              trang_thai=q.FAILED, so_engine=0, so_callback=0)
        # Vao dead-letter o lan dau, khong de no chay het ba luot.
        assert mt.scalar("SELECT attempts FROM review_job") == 1
    print("[PASS] loi auth -> dead-letter o lan dau, khong thu ba lan vo ich")


# ------------------------------------------------- nhom 3: hong tai engine


def test_engine_loi_tam_thoi_thi_retry_va_moi_lan_goi_dung_mot_lan():
    with moi_truong("vf_test_fm_engine") as mt:
        mt.post_job()
        engine = EngineGia(loi=RuntimeError("LLM 529 overloaded"))
        ket = mt.chay(engine=engine)
        _kiem("engine loi", ket=ket["ket"], engine=engine,
              connector=ket["connector"], trang_thai=q.QUEUED,
              so_engine=1, so_callback=0)
        assert mt.scalar("SELECT count(*) FROM run_log") == 0
    print("[PASS] engine loi -> queued, dung 1 lan goi/attempt, khong callback")


def test_ca_bon_agent_thieu_thi_retry_va_khong_ghi_run():
    with moi_truong("vf_test_fm_missing") as mt:
        mt.post_job()
        engine = EngineGia(missing_agents=[
            "content_quality", "seo", "brand", "compliance",
        ])
        ket = mt.chay(engine=engine)
        _kiem("4/4 agent thieu", ket=ket["ket"], engine=engine,
              connector=ket["connector"], trang_thai=q.QUEUED,
              so_engine=1, so_callback=0)
        assert mt.scalar("SELECT count(*) FROM run_log") == 0
    print("[PASS] 4/4 agent thieu -> nghi hong ha tang, retry, khong ghi run")


# ------------------------------------------- nhom 4: hong o buoc ghi ve


def test_callback_apply_nhung_mat_response_thi_retry_idempotent():
    with moi_truong("vf_test_fm_lost") as mt:
        mt.post_job()
        mat = ConnectorGia(
            loi_write=connector_base.ConnectorTransientError("mat response")
        )
        engine = EngineGia()
        lan_dau = mt.chay(engine=engine, connector=mat)
        assert lan_dau["ket"] == q.QUEUED
        run_id_dau = mat.write_calls[0].run_id

        with mt.conn.cursor() as cur:
            cur.execute("UPDATE review_job SET run_after=now(), status='queued'")

        engine_2 = EngineGia()
        lai = ConnectorGia(outcome="already_applied")
        lan_hai = mt.chay(engine=engine_2, connector=lai)

        assert lan_hai["ket"] == q.DONE, lan_hai["ket"]
        assert len(engine_2.calls) == 0, "khong duoc goi LLM lan hai"
        assert len(lai.fetch_calls) == 0, "khong duoc fetch lan hai"
        assert lai.write_calls[0].run_id == run_id_dau, "phai dung lai run_id cu"
        assert mt.scalar("SELECT count(*) FROM run_log") == 1, "chi mot run"
    print("[PASS] callback mat response -> retry cung run_id, 1 engine, 1 run")


def test_revision_cu_hoan_tat_sau_revision_moi_thi_superseded():
    with moi_truong("vf_test_fm_stale") as mt:
        mt.post_job()
        engine = EngineGia()
        connector = ConnectorGia(outcome="content_superseded")
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("stale write", ket=ket["ket"], engine=engine, connector=connector,
              trang_thai=q.SUPERSEDED, so_engine=1, so_callback=1)
        assert mt.scalar("SELECT writeback_status FROM run_log") == "superseded"
        assert mt.scalar("SELECT status FROM review_job") == "superseded"
    print("[PASS] revision cu xong sau revision moi -> superseded, khong ghi de")


def test_job_legacy_v1_van_di_het_duong_trong_cua_so_rollback():
    with moi_truong("vf_test_fm_legacy") as mt:
        mt.xep_job_legacy()
        engine = EngineGia()
        connector = ConnectorGia()
        ket = mt.chay(engine=engine, connector=connector)
        _kiem("legacy v1", ket=ket["ket"], engine=engine, connector=connector,
              trang_thai=q.DONE, so_engine=1, so_callback=1)
        assert connector.fetch_calls[0]["working_copy"] is True
        assert connector.write_calls[0].content_hash == HASH_V1
        assert connector.write_calls[0].content_hash_version == 1
    print("[PASS] job legacy v1 doc working copy, hash 4 field, di het duong")


def test_worker_chet_giua_chung_thi_reclaim_va_dung_lai_run_da_luu():
    with moi_truong("vf_test_fm_crash") as mt:
        mt.post_job()
        # Mo phong worker chet SAU khi ghi run nhung TRUOC khi callback xong.
        treo = ConnectorGia(loi_write=RuntimeError("worker bi kill -9"))
        engine = EngineGia()
        job = mt.claim()
        try:
            mt.chay(job=job, engine=engine, connector=treo)
        except RuntimeError:
            pass
        assert mt.scalar("SELECT count(*) FROM run_log") == 1

        with mt.conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET status='queued', run_after=now(), "
                "claimed_at=NULL"
            )
        engine_2 = EngineGia()
        lai = ConnectorGia(outcome="already_applied")
        lan_hai = mt.chay(engine=engine_2, connector=lai)

        assert lan_hai["ket"] == q.DONE, lan_hai["ket"]
        assert len(engine_2.calls) == 0, "phai dung lai run da luu, khong cham lai"
        assert mt.scalar("SELECT count(*) FROM run_log") == 1
    print("[PASS] worker chet sau khi luu run -> reclaim, dung lai run, khong cham lai")


def test_dead_letter_chi_chay_lai_khi_ep_tuong_minh():
    with moi_truong("vf_test_fm_deadletter") as mt:
        tao = mt.post_job()
        with mt.conn.cursor() as cur:
            cur.execute(
                "UPDATE review_job SET status='failed', attempts=3 WHERE public_id=%s",
                (tao.json()["job_id"],),
            )

        chan = mt.post_job()
        assert chan.status_code == 409, chan.status_code
        assert mt.scalar("SELECT count(*) FROM review_job") == 1

        ep = mt.post_job(force=True, source="manual")
        assert ep.status_code == 202, ep.text
        assert mt.scalar("SELECT count(*) FROM review_job") == 2
        assert mt.scalar(
            "SELECT source FROM review_job WHERE public_id=%s",
            (ep.json()["job_id"],),
        ) == "manual"
    print("[PASS] dead-letter chan tu dong, chi chay lai khi ep tuong minh")


if __name__ == "__main__":
    if not co_postgres():
        print("[SKIP] khong ket noi duoc Postgres; [SKIP] khong phai [PASS]")
        sys.exit(0)

    failed = False
    for fn in (
        test_site_tam_dung_khong_tao_job_va_khong_goi_gi,
        test_token_sai_hoac_revoked_khong_tao_job,
        test_khong_co_profile_khop_khong_tao_job,
        test_revision_bien_mat_thi_dead_letter_khong_goi_LLM,
        test_hash_lech_thi_dead_letter_khong_goi_LLM,
        test_connector_timeout_truoc_engine_thi_retry_khong_ton_tien,
        test_loi_auth_vao_thang_dead_letter_khong_thu_ba_lan,
        test_engine_loi_tam_thoi_thi_retry_va_moi_lan_goi_dung_mot_lan,
        test_ca_bon_agent_thieu_thi_retry_va_khong_ghi_run,
        test_callback_apply_nhung_mat_response_thi_retry_idempotent,
        test_revision_cu_hoan_tat_sau_revision_moi_thi_superseded,
        test_job_legacy_v1_van_di_het_duong_trong_cua_so_rollback,
        test_worker_chet_giua_chung_thi_reclaim_va_dung_lai_run_da_luu,
        test_dead_letter_chi_chay_lai_khi_ep_tuong_minh,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
