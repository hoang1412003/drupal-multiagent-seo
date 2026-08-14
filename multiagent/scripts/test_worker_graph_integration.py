"""Regression offline cho ranh gioi worker -> graph -> Drupal.

Loi khoa ban dau: worker production dung graph mac dinh da co node write_back,
roi tu worker PATCH them lan nua sau audit. Test giu worker va topology graph
that; chi thay cac bien ngoai (Drupal, LLM/agent, audit, queue) bang fake/spy.

Tu Plan 4 test nay khoa them mot thu: worker fetch noi dung MOT lan qua
connector, va graph phai dung lai chinh ban do thay vi goi HTTP lan hai. De
chung minh dieu do that su xay ra, `_request_with_retry` cua drupal_client bi
thay bang ham nem loi - bat ky lan goi HTTP nao cung lam test do ngay.
"""
import os
import sys
from contextlib import nullcontext
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import drupal_client
import graph
import job_queue as q
import worker
from review_platform import fingerprint as platform_fingerprint
from review_platform.connectors import base as connector_base


class _FakeConn:
    def transaction(self):
        return nullcontext()


def _ket_qua(score):
    return {"score": score, "issues": [], "flags": [], "criteria": []}


class _ConnectorGia:
    def __init__(self, tai_lieu):
        self._tai_lieu = tai_lieu
        self.fetch_calls = 0
        self.write_calls = []

    def fetch_content(self, external_content_id, *, external_revision_id=None,
                      working_copy=False):
        self.fetch_calls += 1
        return self._tai_lieu

    def write_back(self, request):
        self.write_calls.append(request)
        return connector_base.WriteBackResult(
            outcome="applied", applied_revision_id="124"
        )


def test_instrumentation_usage_khong_doi_output_cham_diem():
    """Cong cuoi cua Plan 5 Task 3: wrapper usage KHONG duoc doi ket qua cham.

    Chay CUNG mot job hai lan - mot lan khong cai instrumentation, mot lan co -
    roi so payload ghi ve Drupal tung byte. Lech mot ky tu nghia la duong cham
    diem da khac, va E1/E5 do sau nay se do mot he thong khac voi he thong
    duoc thiet ke.

    So payload chu khong so `prompt_version`: prompt_version chi bam noi dung
    prompt, no khong the phat hien wrapper lam doi luong du lieu di qua.
    """
    from review_platform import usage as platform_usage

    khong_boc = _chay_mot_job_qua_graph()

    import ai_core
    from agents import brand_voice, compliance, content_quality, fact_check, seo

    goc = {
        m.__name__: m.call_agent
        for m in (content_quality, seo, brand_voice, compliance, fact_check)
    }
    goc_usage = ai_core.USAGE_LOG
    try:
        platform_usage.install_worker_usage_instrumentation(force=True)
        co_boc = _chay_mot_job_qua_graph()
    finally:
        for m in (content_quality, seo, brand_voice, compliance, fact_check):
            m.call_agent = goc[m.__name__]
        ai_core.USAGE_LOG = goc_usage
        platform_usage._da_cai = False

    assert co_boc["status"] == khong_boc["status"]
    assert co_boc["score"] == khong_boc["score"]
    assert co_boc["suggestions"] == khong_boc["suggestions"]
    # report_json chua scored_at/platform_run_id thay doi moi lan chay - so
    # phan CON LAI, tuc phan phan anh ket qua cham diem.
    bo_qua = {"scored_at", "platform_run_id"}
    a = {k: v for k, v in co_boc["report_json"].items() if k not in bo_qua}
    b = {k: v for k, v in khong_boc["report_json"].items() if k not in bo_qua}
    assert a == b, f"report khac nhau:\n{a}\n{b}"
    print("[PASS] cai instrumentation usage KHONG doi output cham diem")


def _chay_mot_job_qua_graph() -> dict:
    """Chay mot job qua topology graph THAT, tra ve payload ghi sang Drupal.

    Tach rieng de goi duoc hai lan (co/khong co instrumentation) va so ket qua.
    """
    ket = _chay_va_kiem()
    return ket["payload"]


def test_worker_voi_graph_mac_dinh_chi_patch_mot_lan():
    """Bat loi neu graph PATCH truoc khi worker audit va PATCH co quan ly."""
    ket = _chay_va_kiem()
    assert ket["graph_patch_calls"] == [], (
        f"graph khong duoc tu PATCH, thuc te {len(ket['graph_patch_calls'])} lan"
    )
    assert ket["fetch_calls"] == 1, ket["fetch_calls"]
    assert ket["write_calls"] == 1, (
        f"moi job chi duoc callback mot lan, thuc te {ket['write_calls']}"
    )
    assert ket["expected_revision_id"] == "123"
    assert ket["content_hash_version"] == 2


def _chay_va_kiem() -> dict:
    fields = {
        "title": "Huong dan sac xe dien",
        "body": "<p>Noi dung mau day du de chay graph.</p>",
        "summary": "Tom tat mau",
        "meta_description": "Mo ta mau",
        "url_alias": "/huong-dan-sac-xe-dien",
        "image_alt": "Xe dien dang sac",
    }
    node_id = "00000000-0000-0000-0000-000000000901"
    job = {
        "id": 901,
        "node_id": node_id,
        "external_content_id": node_id,
        "external_revision_id": "123",
        "content_hash": platform_fingerprint.input_fingerprint(fields),
        "content_hash_version": 2,
        "site_id": UUID("00000000-0000-4000-8000-000000000001"),
        "profile_id": UUID("00000000-0000-4000-8000-000000000002"),
        "policy_version": "cam-nang-vn-v1",
        "content_type": "cam_nang",
        "langcode": "vi",
        "correlation_id": uuid4(),
        "source": "event",
        "supersedes_job_id": None,
        "attempts": 1,
    }
    connector = _ConnectorGia(
        connector_base.ContentDocument(
            fields=fields,
            raw_content={"data": {}},
            source_url="http://drupal.ddev.site/node/901",
            external_revision_id="123",
            content_type="cam_nang",
            langcode="vi",
        )
    )
    graph_patch_calls = []

    def _khong_duoc_goi_http(*args, **kwargs):
        raise AssertionError(
            "graph goi HTTP lan hai thay vi dung prepared document cua worker"
        )

    replacements = [
        # Giu NGUYEN fetch_content that de di xuyen qua duong delegation moi.
        (graph, "fetch_content", drupal_client.fetch_content),
        (drupal_client, "_request_with_retry", _khong_duoc_goi_http),
        (graph.content_quality, "run", lambda article: _ket_qua(80.0)),
        (graph.seo, "run", lambda article: _ket_qua(80.0)),
        (graph.brand_voice, "run", lambda article, **keys: _ket_qua(80.0)),
        (graph.compliance, "run", lambda article, **keys: _ket_qua(80.0)),
        (graph, "write_back", lambda **payload: (
            graph_patch_calls.append(payload), True)[1]),
        (audit, "find_reusable_writeback", lambda conn, *, job: None),
        (audit, "ghi_scoped", lambda conn, **data: 1),
        (audit, "mark_writeback", lambda conn, run_id, **data: None),
        (q, "complete", lambda conn, job_id: None),
        (q, "fail", lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError(f"job khong duoc fail: {args} {kwargs}"))),
        (q, "fail_permanent", lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError(f"job khong duoc dead-letter: {args} {kwargs}"))),
    ]
    originals = [(obj, name, getattr(obj, name))
                 for obj, name, _replacement in replacements]
    for obj, name, replacement in replacements:
        setattr(obj, name, replacement)
    try:
        result = worker.chay_mot_job(_FakeConn(), job, connector=connector)
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)

    assert result == q.DONE, result
    yeu_cau = connector.write_calls[0] if connector.write_calls else None
    return {
        "graph_patch_calls": graph_patch_calls,
        "fetch_calls": connector.fetch_calls,
        "write_calls": len(connector.write_calls),
        "expected_revision_id": None if yeu_cau is None else yeu_cau.expected_revision_id,
        "content_hash_version": None if yeu_cau is None else yeu_cau.content_hash_version,
        "payload": None if yeu_cau is None else {
            "status": yeu_cau.status,
            "score": yeu_cau.score,
            "suggestions": yeu_cau.suggestions,
            "report_json": yeu_cau.report_json,
        },
    }


if __name__ == "__main__":
    failed = False
    for fn in (
        test_worker_voi_graph_mac_dinh_chi_patch_mot_lan,
        test_instrumentation_usage_khong_doi_output_cham_diem,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    if not failed:
        print("[PASS] worker + graph that: 1 fetch, 0 PATCH tu graph, 1 callback")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
