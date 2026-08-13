"""Worker: nhan job tu hang doi, goi pipeline, ghi log, PATCH ve Drupal.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md

Tien trinh RIENG voi api.py, co y (spec muc 3.3): API phai tra loi trong vai
ms trong khi worker chay 30-60 giay moi job; worker nap BGE-M3 (~2GB) luc
khoi dong con API thi khong can. Worker chet vi het RAM thi API van song va
job van xep hang duoc - do chinh la ly do co hang doi.

Chay (tu multiagent/): .venv\\Scripts\\python.exe src\\worker.py
"""
import logging
import os
from pathlib import Path
import socket
import sys
import time
from uuid import uuid4

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ai_core
import audit
import config
import job_queue as q
import reconcile
import text_utils
from review_platform import database as platform_database
from review_platform import migrations

NGU_KHI_RONG_GIAY = 2
CHU_KY_DOI_SOAT_GIAY = 300
_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _payload_tu_state(state: dict) -> dict:
    """Bon gia tri se PATCH sang Drupal: status, score, suggestions, report_json.

    CACH LAM: chan `graph.write_back` roi goi `graph.write_back_node(state)`.
    Ham do dung san ca bon gia tri va goi write_back(...) voi dung chung; chan
    lai la lay duoc nguyen ven ma KHONG PATCH gi.

    Vi sao khong chep logic dung chuoi goi y sang day: no gom loi theo tung
    field, sap thu tu field, them tien to [LUU Y]/[LY DO TU CHOI]. Chep sang
    worker la tao ban thu hai cua cung mot chuoi - dung loai trung lap ma
    config-spec.md muc 1 ghi lai nhu mot loi da tra gia (cung mot con so nam o
    5 noi va da troi lech hai lan).

    `write_back_node` doc decision/final_score tu STATE chu khong tu `report`,
    va giu nguyen tinh chat do la co y: do dung la nguon ghi vao
    field_ai_status/field_ai_score.
    """
    import graph

    da_bat = {}
    that = graph.write_back
    graph.write_back = lambda **kw: (da_bat.update(kw), True)[1]
    try:
        graph.write_back_node(state)
    finally:
        graph.write_back = that

    da_bat.pop("node_id", None)      # worker tu truyen, khong lay tu day
    return da_bat


def chay_mot_job(conn, job: dict, *, invoke=None, write_back_fn=None) -> str:
    """Xu ly mot job da claim. Tra trang thai cuoi: done / queued / failed."""
    from drupal_client import write_back as _write_back_that

    if write_back_fn is None:
        write_back_fn = _write_back_that

    node_id, chash = job["node_id"], job["content_hash"]

    # CHOT CHAN TIEN: da cham dung noi dung nay roi thi chi ghi lai ket qua,
    # KHONG goi LLM. Duong nay xay ra khi lan truoc pipeline chay xong nhung
    # PATCH that bai. Cham lai ton $0,057 that.
    cu = audit.find_reusable_writeback(conn, job=job)
    if cu is not None:
        if write_back_fn(node_id=node_id, **cu["payload"]):
            with conn.transaction():
                audit.mark_writeback(conn, cu["id"], status="succeeded")
                q.complete(conn, job["id"])
            return q.DONE
        with conn.transaction():
            audit.mark_writeback(
                conn,
                cu["id"],
                status="failed",
                error="write-back that bai (ghi lai ket qua cu)",
            )
            return q.fail(conn, job["id"], "write-back that bai (ghi lai ket qua cu)")

    if invoke is None:
        from graph import build_graph

        # Worker phai ghi audit TRUOC khi PATCH va tu quan ly retry neu PATCH
        # that bai. Graph co write-back rieng se PATCH som mot lan ngoai ranh
        # gioi nay, roi worker PATCH lan hai sau audit.
        invoke = build_graph(include_write_back=False).invoke

    ai_core.USAGE_LOG.clear()
    da_ghi_usage = False
    bat_dau = time.monotonic()
    try:
        try:
            # CHI truyen node_id. content_type/langcode do graph._khoa_cua() suy
            # ra - do la CHO DUY NHAT duoc phep suy ra cap khoa nay (no B6).
            # Worker dat them mot duong thu hai la dung lai dung cai bay vua dep.
            state = invoke({"node_id": node_id})
        except Exception as e:
            return q.fail(conn, job["id"], f"{e.__class__.__name__}: {e}")
        duration_ms = int((time.monotonic() - bat_dau) * 1000)

        # Import o day (khong o dau module) de tranh nap ca chuoi phu thuoc
        # nang cua graph.py (langgraph, agents, ...) khi worker chi can
        # invoke() gia trong test. graph.AGENT_LABELS thay cho hang so chep
        # tay _SO_AGENT = 4 cu: them agent thu 5 se tu dong doi nguong "hong
        # ha tang", khong con phai sua tay o hai noi.
        import graph

        report = state.get("report") or {}
        if len(report.get("missing_agents") or []) >= len(graph.AGENT_LABELS):
            return q.fail(
                conn,
                job["id"],
                "ca 4 agent khong tra ket qua - nghi hong ha tang",
            )

        run_public_id = uuid4()
        payload = _payload_tu_state(state)
        # config_meta phai tra theo DUNG cap khoa ma chinh lan cham nay dung -
        # goi graph.khoa_cua(state) chu KHONG duoc tu goi config.load() khong
        # tham so: cai do roi ve mac dinh CUA config.load(), tinh co trung
        # DEFAULT_CONTENT_TYPE/DEFAULT_LANGCODE cua graph.py hom nay nhung la
        # hai hang so doc lap o hai file, dung loai "mot con so nhieu noi" ma
        # scoring.yaml duoc dung ra de chan (config-spec.md muc 1).
        khoa = graph.khoa_cua(state)

        # CRITICAL: ghi run_log theo hash NOI DUNG THAT DA CHAM (state["fields"]),
        # KHONG theo job["content_hash"] (`chash`). fetch_content() lay revision
        # MAC DINH cua node, khong co resourceVersion: voi bai DA XUAT BAN roi
        # dua sang needs_review (default_revision=false), revision mac dinh van
        # la ban CU da xuat ban - invoke() cham nham noi dung cu trong khi hook
        # gui hash cua ban nhap moi. Ghi theo `chash` trong truong hop do se
        # ghi sai chinh nhat ky truy vet, va reusable lookup sau nay se tra payload
        # sai cho hash do vinh vien, khong bao gio goi lai LLM de sua.
        hash_that = text_utils.content_hash(state.get("fields") or {})
        if hash_that != chash:
            logging.warning(
                "[worker] job %s (node %s): hash job=%s nhung hash noi dung "
                "THAT DA CHAM=%s - lech nhau. Nguyen nhan co the la "
                "fetch_content() tra ve revision MAC DINH (ban da xuat ban) "
                "thay vi ban nhap moi qua JSON:API.",
                job["id"], node_id, chash, hash_that,
            )

        run_db_id = audit.ghi_scoped(
            conn,
            run_public_id=run_public_id,
            job=job,
            content_hash=hash_that,
            duration_ms=duration_ms, report=report,
            config_meta=config.load(**khoa).get("meta") or {},
            usage=list(ai_core.USAGE_LOG), model=ai_core.MODEL, payload=payload,
        )
        da_ghi_usage = True

        if write_back_fn(node_id=node_id, **payload):
            with conn.transaction():
                audit.mark_writeback(conn, run_db_id, status="succeeded")
                q.complete(conn, job["id"])
            return q.DONE
        with conn.transaction():
            audit.mark_writeback(
                conn,
                run_db_id,
                status="failed",
                error="write-back that bai",
            )
            return q.fail(conn, job["id"], "write-back that bai")
    finally:
        # USAGE_LOG la list muc module, KHONG tu xoa (ai_core.py). Luon dam
        # bao no rong khi ra khoi ham, ke ca hai nhanh thoat som (invoke() nem
        # loi, ca 4 agent thieu): khong lam vay thi tien LLM da tieu o lan
        # chay hong do khong duoc ghi vao dau (khong co run_log cho ca nay) va
        # bien mat lang le khi job KE TIEP tu clear() dau ham.
        if ai_core.USAGE_LOG and not da_ghi_usage:
            logging.warning(
                "[worker] job %s (node %s) that bai truoc khi ghi duoc "
                "run_log nhung da tieu %d lan goi LLM: %s",
                job["id"], node_id, len(ai_core.USAGE_LOG), ai_core.USAGE_LOG,
            )
        ai_core.USAGE_LOG.clear()


def _xu_ly_tiep_theo(conn, ten: str, *, invoke=None, write_back_fn=None):
    """Nhan va xu ly MOT job, neu hang doi con viec. Rong -> tra None.

    Loi bat ngo trong chay_mot_job() (audit.ghi_scoped, q.complete, q.fail,
    write_back_fn tu no rieng nem loi ...) KHONG duoc de thoat ra ngoai va
    giet ca vong_lap(): mot job hong khong duoc keo theo ca tien trinh, va
    job dang ket o `running` phai doi toi 15 phut moi duoc reclaim_stuck()
    thu hoi. Kich ban te nhat: audit.ghi_scoped() nem loi SAU khi pipeline da chay
    ton tien nhung TRUOC khi INSERT xong run_log - khong dua job ve
    queued/failed ngay o day thi lan sau reusable lookup khong thay ban ghi, goi
    lai LLM, tra tien lan hai - dung thu chot chan tien duoc dung ra de ngan.
    """
    job = q.claim(conn, ten)
    if job is None:
        return None
    logging.info("[worker %s] cham node %s (lan %d)", ten, job["node_id"],
                 job["attempts"])
    try:
        ket = chay_mot_job(conn, job, invoke=invoke, write_back_fn=write_back_fn)
    except Exception as e:
        logging.error("[worker %s] job %s (node %s) loi ngoai y muon: %s",
                      ten, job["id"], job["node_id"], e)
        ket = q.fail(conn, job["id"], f"{e.__class__.__name__}: {e}")
    logging.info("[worker %s] node %s -> %s", ten, job["node_id"], ket)
    return ket


def _vong_lap_voi_conn(conn, ten: str) -> None:
    ten = ten or f"{socket.gethostname()}:{os.getpid()}"
    migrations.require_current(conn, _MIGRATIONS_DIR)

    # Nap model NGAY luc khoi dong, khong de lazy trong lan cham dau
    # (docs/rag-design.md muc 6): lan cham dau se cham them vai giay va nguoi
    # dung tuong he thong treo.
    from embeddings import get_default_embedder

    get_default_embedder()
    logging.info("[worker %s] san sang", ten)

    lan_doi_soat = 0.0
    while True:
        q.reclaim_stuck(conn)
        if time.monotonic() - lan_doi_soat >= CHU_KY_DOI_SOAT_GIAY:
            lan_doi_soat = time.monotonic()
            try:
                them = reconcile.quet(conn)
                if them:
                    logging.info("[worker %s] doi soat them %d job", ten, them)
            except Exception as e:
                # Doi soat hong KHONG duoc lam chet worker - duong event van chay
                logging.warning("[worker %s] doi soat loi: %s", ten, e)

        if _xu_ly_tiep_theo(conn, ten) is None:
            time.sleep(NGU_KHI_RONG_GIAY)


def vong_lap(conn=None, ten: str = "") -> None:
    """Chay worker tren mot connection rieng trong suot vong doi process.

    Tham so ``conn`` chi giu cho test/compatibility; production khong chia se
    connection cache cua KB/API.
    """
    if conn is not None:
        _vong_lap_voi_conn(conn, ten)
        return
    with platform_database.open_connection() as dedicated_conn:
        _vong_lap_voi_conn(dedicated_conn, ten)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    vong_lap()
