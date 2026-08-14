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
from review_platform import fingerprint as platform_fingerprint
from review_platform import migrations, sites
from review_platform.connectors import base as connector_base
from review_platform.connectors import runtime as connector_runtime

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


def _connector_cho_job(conn, job: dict):
    """Connector cua DUNG site so huu job; secret lay tu env theo secret_ref."""
    from review_platform.connectors import secrets as connector_secrets
    from review_platform.connectors.drupal import DrupalConnector

    site = sites.load_site_by_id(conn, job["site_id"])
    return DrupalConnector(site, connector_secrets.resolve(site.secret_ref))


def _fingerprint(fields: dict, version: int) -> str:
    """Chon thuat toan theo DUNG version cua job.

    Job legacy mang version 1 (bon field, `text_utils.content_hash`); job tu
    /api/v1 mang version 2 (sau field). Ep job v1 di qua v2 se lam moi job
    legacy bao `input_hash_mismatch` - tuc cua so rollback coi nhu khong co.
    """
    if int(version) == platform_fingerprint.VERSION:
        return platform_fingerprint.input_fingerprint(fields)
    return text_utils.content_hash(fields)


def _loi_connector_thanh_trang_thai(conn, job: dict, exc: Exception) -> str:
    """Loi thu lai duoc -> queued co backoff. Loi khong thu lai duoc -> dead-letter.

    Phan biet o day de mot job sai quyen khong goi LLM ba lan roi that bai ba
    lan. `q.fail` la tang DUY NHAT quyet dinh backoff va tran so lan thu.
    """
    if isinstance(exc, connector_base.ConnectorTransientError):
        return q.fail(
            conn,
            job["id"],
            f"llm_transient: {exc}",
            retry_after_seconds=exc.retry_after_seconds,
        )
    if isinstance(exc, connector_base.ConnectorError):
        return q.fail_permanent(conn, job["id"], exc.ma, str(exc))
    raise exc


def _gui_ket_qua(
    conn,
    job: dict,
    connector,
    *,
    run_db_id: int,
    run_public_id,
    payload: dict,
    expected_revision_id,
    content_hash: str,
    content_hash_version: int,
) -> str:
    """Goi result callback DUNG MOT LAN va quy ket qua ve trang thai job."""
    yeu_cau = connector_base.WriteBackRequest(
        run_id=run_public_id,
        external_content_id=job["external_content_id"],
        expected_revision_id=expected_revision_id,
        content_hash=content_hash,
        content_hash_version=content_hash_version,
        status=payload.get("status"),
        score=payload.get("score"),
        suggestions=payload.get("suggestions") or "",
        report_json=payload.get("report_json") or {},
    )
    try:
        ket_qua = connector.write_back(yeu_cau)
    except connector_base.ConnectorError as exc:
        with conn.transaction():
            audit.mark_writeback(
                conn, run_db_id, status="failed", error=f"writeback_failed: {exc}"
            )
        return _loi_connector_thanh_trang_thai(conn, job, exc)

    if ket_qua.outcome in ("applied", "already_applied"):
        with conn.transaction():
            audit.mark_writeback(conn, run_db_id, status="succeeded")
            q.complete(conn, job["id"])
        return q.DONE

    # content_superseded: noi dung da co revision moi hon. Job nay ket thuc o
    # trang thai `superseded` - KHONG retry payload cu len noi dung moi, va
    # cung khong tinh la that bai. Hai buoc nam trong cung mot transaction de
    # khong bao gio ton tai trang thai nua voi.
    with conn.transaction():
        audit.mark_writeback(conn, run_db_id, status="superseded")
        q.supersede(conn, job["id"])
    return q.SUPERSEDED


def chay_mot_job(
    conn,
    job: dict,
    *,
    invoke=None,
    connector=None,
    connector_factory=None,
    fixture_run: bool = False,
) -> str:
    """Xu ly mot job da claim. Tra trang thai cuoi: done/queued/failed/superseded."""
    node_id = job["external_content_id"]
    chash = job["content_hash"]
    version = int(job.get("content_hash_version") or 1)

    # CHOT CHAN TIEN: da cham dung noi dung nay roi thi chi gui lai ket qua,
    # KHONG goi LLM. Duong nay xay ra khi lan truoc pipeline chay xong nhung
    # callback that bai. Cham lai ton $0,057 that.
    cu = audit.find_reusable_writeback(conn, job=job)

    if connector is None:
        try:
            connector = (connector_factory or _connector_cho_job)(conn, job)
        except (connector_base.ConnectorError, sites.ContextSelectionError) as exc:
            return q.fail_permanent(conn, job["id"], "connector_auth", str(exc))

    if cu is not None:
        # Dung DUNG run_id/precondition cu: nho vay Drupal nhan ra day la lan
        # gui lai cua cung mot run va tra `already_applied` thay vi tao them
        # mot revision thu hai.
        return _gui_ket_qua(
            conn,
            job,
            connector,
            run_db_id=cu["id"],
            run_public_id=cu["run_id"],
            payload=cu["payload"],
            expected_revision_id=cu["external_revision_id"],
            content_hash=cu["content_hash"],
            content_hash_version=version,
        )

    # Prefetch TRUOC khi goi LLM. Job v2 luon biet revision; job legacy v1
    # khong biet nen phai doc working copy roi lay revision that tu response.
    try:
        tai_lieu = connector.fetch_content(
            node_id,
            external_revision_id=job.get("external_revision_id"),
            working_copy=job.get("external_revision_id") is None,
        )
    except connector_base.ConnectorError as exc:
        return _loi_connector_thanh_trang_thai(conn, job, exc)

    # Kiem fingerprint TRUOC LLM. Lech nghia la noi dung tren Drupal khong con
    # la noi dung ma job mo ta - cham no roi ghi ket qua duoi nhan cua hash cu
    # se tao mot ban ghi noi doi ma khong ai phat hien duoc.
    thuc_te = _fingerprint(tai_lieu.fields, version)
    if thuc_te != chash:
        return q.fail_permanent(
            conn,
            job["id"],
            "input_hash_mismatch",
            f"job mong doi {chash[:12]} nhung noi dung hien tai la {thuc_te[:12]} "
            f"(hash version {version})",
        )

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
            # Truyen tuong minh cap khoa CUA JOB thay vi de graph roi ve mac
            # dinh: tu Plan 4, scope den tu profile cua site chu khong con la
            # hang so. graph._khoa_cua() van do mac dinh cho script thu cong.
            #
            # `runtime.activate` cho graph dung lai chinh tai lieu vua fetch,
            # nen ca job chi doc Drupal DUNG MOT LAN va khong the doc trung
            # hai revision khac nhau.
            with connector_runtime.activate(connector, node_id, tai_lieu):
                state = invoke({
                    "node_id": node_id,
                    "content_type": job["content_type"],
                    "langcode": job["langcode"],
                })
        except Exception as e:
            return q.fail(conn, job["id"], f"internal: {e.__class__.__name__}: {e}")
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

        # Hash da duoc kiem KHOP truoc khi goi LLM, nen tu day tro di
        # job["content_hash"] chinh la hash cua noi dung vua cham. Con canh
        # bao lech o duong cu la vi luc do worker chua fetch truoc va graph
        # co the doc phai revision mac dinh; nay khong con kha nang do.
        hash_that = _fingerprint(state.get("fields") or tai_lieu.fields, version)
        if hash_that != chash:
            logging.warning(
                "[worker] job %s (node %s): graph tra ve fields co hash %s "
                "khac hash da kiem %s - kiem lai runtime prepared document.",
                job["id"], node_id, hash_that, chash,
            )

        # Bao cao ghi sang Drupal phai mang dung ba thu de callback CAS so
        # duoc: hash cua job, version cua hash do, va run ID cong khai lam
        # khoa idempotency.
        report_json = dict(payload.get("report_json") or {})
        report_json["content_hash"] = chash
        report_json["content_hash_version"] = version
        report_json["platform_run_id"] = str(run_public_id)
        payload["report_json"] = report_json

        run_db_id = audit.ghi_scoped(
            conn,
            run_public_id=run_public_id,
            job=job,
            content_hash=chash,
            duration_ms=duration_ms, report=report,
            config_meta=config.load(**khoa).get("meta") or {},
            usage=list(ai_core.USAGE_LOG), model=ai_core.MODEL, payload=payload,
            content_hash_version=version,
            source_url=tai_lieu.source_url,
            is_fixture=fixture_run,
            external_revision_id=tai_lieu.external_revision_id,
        )
        da_ghi_usage = True

        return _gui_ket_qua(
            conn,
            job,
            connector,
            run_db_id=run_db_id,
            run_public_id=run_public_id,
            payload=payload,
            expected_revision_id=tai_lieu.external_revision_id,
            content_hash=chash,
            content_hash_version=version,
        )
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


def _xu_ly_tiep_theo(conn, ten: str, *, invoke=None, connector=None,
                     connector_factory=None):
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
        ket = chay_mot_job(
            conn, job, invoke=invoke, connector=connector,
            connector_factory=connector_factory,
        )
    except Exception as e:
        logging.error("[worker %s] job %s (node %s) loi ngoai y muon: %s",
                      ten, job["id"], job["node_id"], e)
        ket = q.fail(conn, job["id"], f"internal: {e.__class__.__name__}: {e}")
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
