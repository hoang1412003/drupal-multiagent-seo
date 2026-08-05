"""Test build_kb: kiem cach cat chunk va cac dong san de INSERT.

Khong can Postgres: kiem `chuan_bi_rows()` - phan THUAN, tach ra khoi build()
dung de test giu duoc tinh chat "khong can ha tang". Phan ghi that do bang
scripts/eval_retrieval.py (E2).
Chay: .venv\\Scripts\\python.exe scripts\\test_kb_build.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kb import build_kb


class FakeEmbedder:
    _VOCAB = ["VF 5", "VF 8", "VF 9", "bảo dưỡng"]

    def embed(self, texts):
        out = []
        for t in texts:
            v = [1.0 if x.lower() in t.lower() else 0.0 for x in self._VOCAB]
            if sum(v) == 0:
                v = [1.0] + [0.0] * (len(self._VOCAB) - 1)
            out.append(v)
        return out

    @property
    def dim(self):
        return len(self._VOCAB)


def _entries():
    with open(build_kb.SPECS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_chunk_has_model_context():
    entry = {"model": "VF 8", "specs": {"tam_hoat_dong": "420km"}}
    text = build_kb.chunk_text(entry)
    assert "VF 8" in text, "chunk phai chua ten model (Contextual Retrieval)"
    assert "420km" in text, "chunk phai chua gia tri thong so"
    print("[PASS] chunk_text co ngu canh model")


def test_dem_dung_so_chunk():
    rows = build_kb.chuan_bi_rows(_entries(), FakeEmbedder())
    assert len(rows) == 4, f"phai co 4 chunk (seed), thuc te {len(rows)}"
    print("[PASS] chuan_bi_rows ra dung so chunk")


def test_chunk_id_duy_nhat_va_co_khoa_phan_vung():
    rows = build_kb.chuan_bi_rows(_entries(), FakeEmbedder())
    ids = [r[1] for r in rows]
    assert len(set(ids)) == len(ids), f"chunk_id bi trung: {ids}"
    # chunk_id la mot phan cua khoa chinh (collection, chunk_id) - trung nhau
    # thi INSERT te giua chung, KB nap do dang.
    assert all(i.startswith("cam_nang:vi:") for i in ids), ids
    print("[PASS] chunk_id duy nhat va mang khoa phan vung")


def test_cot_phan_vung_va_meta():
    rows = build_kb.chuan_bi_rows(_entries(), FakeEmbedder())
    collection, _cid, doc, vec, content_type, langcode, meta = rows[0]
    assert collection == "kb_factcheck", collection
    assert content_type == "cam_nang" and langcode == "vi", (content_type, langcode)
    assert vec.startswith("[") and vec.endswith("]"), vec[:20]
    m = json.loads(meta)
    assert "model" in m and "verified" in m and "source_url" in m, m
    assert m["model"] in doc, "meta.model phai khop noi dung chunk"
    print("[PASS] cot phan vung + meta dung hinh dang")


def test_moi_muc_kb_da_verified():
    """4/4 muc phai `verified: true` (docs/goldset/sources.md muc 2).

    Kiem o day vi day la noi du lieu di vao he thong: mot muc chua verify lot
    vao KB la CP3 doi chieu bang so chua ai kiem, ma CP3 di thang toi co
    `critical` -> veto.
    """
    chua = [e["model"] for e in _entries() if not e.get("verified")]
    assert not chua, f"con muc chua verify: {chua}"
    print("[PASS] 4/4 muc KB da verified")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_chunk_has_model_context,
        test_dem_dung_so_chunk,
        test_chunk_id_duy_nhat_va_co_khoa_phan_vung,
        test_cot_phan_vung_va_meta,
        test_moi_muc_kb_da_verified,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
