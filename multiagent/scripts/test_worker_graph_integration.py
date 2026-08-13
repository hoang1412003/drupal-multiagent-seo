"""Regression offline cho ranh gioi worker -> graph -> Drupal.

Loi khoa: worker production dung graph mac dinh da co node write_back, roi
tu worker PATCH them lan nua sau audit. Test giu worker va topology graph that;
chi thay cac bien ngoai (Drupal, LLM/agent, audit, queue) bang fake/spy.
"""
import os
import sys
from contextlib import nullcontext

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import drupal_client
import graph
import job_queue as q
import text_utils
import worker


class _FakeConn:
    def transaction(self):
        return nullcontext()


def _ket_qua(score):
    return {"score": score, "issues": [], "flags": [], "criteria": []}


def test_worker_voi_graph_mac_dinh_chi_patch_mot_lan():
    """Bat loi neu graph PATCH truoc khi worker audit va PATCH co quan ly."""
    fields = {
        "title": "Huong dan sac xe dien",
        "body": "<p>Noi dung mau day du de chay graph.</p>",
        "summary": "Tom tat mau",
        "meta_description": "Mo ta mau",
        "url_alias": "/huong-dan-sac-xe-dien",
        "image_alt": "Xe dien dang sac",
    }
    job = {
        "id": 901,
        "node_id": "00000000-0000-0000-0000-000000000901",
        "content_hash": text_utils.content_hash(fields),
        "attempts": 1,
    }
    patch_calls = []

    def patch_spy(**payload):
        patch_calls.append(payload)
        return True

    replacements = [
        (graph, "fetch_content", lambda node_id: {
            "fields": fields, "raw_content": {"data": {}}}),
        (graph.content_quality, "run", lambda article: _ket_qua(80.0)),
        (graph.seo, "run", lambda article: _ket_qua(80.0)),
        (graph.brand_voice, "run",
         lambda article, **keys: _ket_qua(80.0)),
        (graph.compliance, "run",
         lambda article, **keys: _ket_qua(80.0)),
        (graph, "write_back", patch_spy),
        (drupal_client, "write_back", patch_spy),
        (audit, "find_reusable_writeback", lambda conn, *, job: None),
        (audit, "ghi_scoped", lambda conn, **data: 1),
        (audit, "mark_writeback", lambda conn, run_id, **data: None),
        (q, "complete", lambda conn, job_id: None),
        (q, "fail", lambda *args: (_ for _ in ()).throw(
            AssertionError(f"job khong duoc fail: {args}"))),
    ]
    originals = [(obj, name, getattr(obj, name))
                 for obj, name, _replacement in replacements]
    for obj, name, replacement in replacements:
        setattr(obj, name, replacement)
    try:
        result = worker.chay_mot_job(_FakeConn(), job)
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)

    assert result == q.DONE, result
    assert len(patch_calls) == 1, (
        f"moi job chi duoc PATCH mot lan, thuc te {len(patch_calls)}"
    )


if __name__ == "__main__":
    test_worker_voi_graph_mac_dinh_chi_patch_mot_lan()
    print("[PASS] worker + graph mac dinh chi PATCH mot lan")
