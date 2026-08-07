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
import socket
import sys
import time

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ai_core
import audit
import config
import db
import job_queue as q
import reconcile

NGU_KHI_RONG_GIAY = 2
CHU_KY_DOI_SOAT_GIAY = 300

# 4/4 agent thieu = hong ha tang, khong phai ket qua danh gia. 1-3 agent thieu
# thi CHAP NHAN: do dung la tinh huong fail-safe architecture.md muc 6.4 duoc
# thiet ke de xu ly (chia lai trong so, ghi note "diem chua day du"). Retry
# luc do la tra tien lan hai cho mot co che dang hoat dong dung.
_SO_AGENT = 4


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
    cu = audit.da_cham(conn, node_id, chash)
    if cu is not None:
        if write_back_fn(node_id=node_id, **cu["payload"]):
            q.complete(conn, job["id"])
            return q.DONE
        return q.fail(conn, job["id"], "write-back that bai (ghi lai ket qua cu)",
                      job["attempts"])

    if invoke is None:
        from graph import build_graph

        invoke = build_graph().invoke

    ai_core.USAGE_LOG.clear()
    bat_dau = time.monotonic()
    try:
        # CHI truyen node_id. content_type/langcode do graph._khoa_cua() suy ra
        # - do la CHO DUY NHAT duoc phep suy ra cap khoa nay (no B6). Worker
        # dat them mot duong thu hai la dung lai dung cai bay vua dep.
        state = invoke({"node_id": node_id})
    except Exception as e:
        return q.fail(conn, job["id"], f"{e.__class__.__name__}: {e}",
                      job["attempts"])
    duration_ms = int((time.monotonic() - bat_dau) * 1000)

    report = state.get("report") or {}
    if len(report.get("missing_agents") or []) >= _SO_AGENT:
        return q.fail(conn, job["id"],
                      "ca 4 agent khong tra ket qua - nghi hong ha tang",
                      job["attempts"])

    payload = _payload_tu_state(state)
    audit.ghi(
        conn, job_id=job["id"], node_id=node_id, content_hash=chash,
        duration_ms=duration_ms, report=report,
        config_meta=config.load().get("meta") or {},
        usage=list(ai_core.USAGE_LOG), model=ai_core.MODEL, payload=payload,
    )
    ai_core.USAGE_LOG.clear()

    if write_back_fn(node_id=node_id, **payload):
        q.complete(conn, job["id"])
        return q.DONE
    return q.fail(conn, job["id"], "write-back that bai", job["attempts"])


def vong_lap(conn=None, ten: str = "") -> None:
    if conn is None:
        conn = db.get_conn()
    ten = ten or f"{socket.gethostname()}:{os.getpid()}"
    q.dam_bao_bang(conn)
    audit.dam_bao_bang(conn)

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

        job = q.claim(conn, ten)
        if job is None:
            time.sleep(NGU_KHI_RONG_GIAY)
            continue
        logging.info("[worker %s] cham node %s (lan %d)", ten, job["node_id"],
                     job["attempts"])
        ket = chay_mot_job(conn, job)
        logging.info("[worker %s] node %s -> %s", ten, job["node_id"], ket)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    vong_lap()
